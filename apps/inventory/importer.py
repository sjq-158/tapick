import csv
import io
import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.home.models import Inventory, Medicine
from apps.register.models import Branch

# Canonical field name mappings for intelligent header detection
FIELD_ALIASES = {
    "medicine_name": [
        "medicine_name", "med_name", "medicine", "name", "drug_name",
        "item_name", "product_name", "product", "item", "title",
    ],
    "generic_name": [
        "generic_name", "generic", "active_ingredient", "formula",
        "scientific_name", "generic_drug_name",
    ],
    "brand_name": [
        "brand_name", "brand", "trade_name", "manufacturer", "maker",
    ],
    "category": [
        "category", "classification", "type", "group", "class", "department",
    ],
    "unit_of_measure": [
        "unit_of_measure", "unit", "uom", "form", "packaging",
        "dosage_form", "measure",
    ],
    "unit_price": [
        "unit_price", "price", "cost", "unit_cost", "rate", "amount",
        "selling_price", "srp",
    ],
    "quantity_on_hand": [
        "quantity_on_hand", "quantity", "qty", "stock", "on_hand",
        "stock_count", "inventory", "current_stock", "count",
    ],
    "reorder_threshold": [
        "reorder_threshold", "reorder_level", "threshold", "min_stock",
        "reorder_point", "minimum_stock", "reorder", "min_qty",
    ],
    "branch": [
        "branch_name", "branch", "store", "location", "outlet",
        "branch_id", "store_name",
    ],
    "requires_prescription": [
        "requires_prescription", "prescription_required", "prescription",
        "rx", "rx_required", "needs_prescription",
    ],
}


def _clean_key(key):
    """Normalize a header string: lower-case, strip whitespace, remove quotes/special chars."""
    if not key:
        return ""
    clean = str(key).strip().lower().replace("-", "_").replace(" ", "_")
    return "".join(c for c in clean if c.isalnum() or c == "_")


def _match_column(header):
    """Identify which canonical field a header corresponds to."""
    clean = _clean_key(header)
    for canonical, aliases in FIELD_ALIASES.items():
        if clean == canonical or clean in aliases:
            return canonical
        # Partial match if alias is substring
        for alias in aliases:
            if alias in clean or clean in alias:
                return canonical
    return None


def _parse_bool(val):
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("true", "1", "yes", "y", "t", "rx", "required")


def _parse_int(val, default=0):
    try:
        if val is None or str(val).strip() == "":
            return default
        # Strip commas or currency signs
        cleaned = str(val).replace(",", "").replace("$", "").replace("₱", "").strip()
        return int(float(cleaned))
    except (ValueError, TypeError):
        return default


def _parse_decimal(val, default=Decimal("0.00")):
    try:
        if val is None or str(val).strip() == "":
            return default
        cleaned = str(val).replace(",", "").replace("$", "").replace("₱", "").strip()
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _decode_file(file_obj):
    """Read an uploaded file and decode it into a unicode string, trying common encodings."""
    raw = file_obj.read()
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252", "iso-8859-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_file_content(file_obj, filename=""):
    """
    Parse an uploaded file (CSV, TSV, JSON) into a list of normalized row dictionaries.
    Returns: (list_of_rows, error_message)
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    text = _decode_file(file_obj)

    # 1. Try JSON if extension is json or content starts with [ or {
    if ext == "json" or text.strip().startswith(("[", "{")):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                # Search for list key like 'items', 'medicines', 'data', 'inventory'
                for k in ("items", "medicines", "data", "inventory", "records"):
                    if k in data and isinstance(data[k], list):
                        data = data[k]
                        break
                else:
                    data = [data]
            if isinstance(data, list):
                rows = []
                for item in data:
                    if isinstance(item, dict):
                        row = {}
                        for k, v in item.items():
                            canonical = _match_column(k)
                            if canonical:
                                row[canonical] = v
                        if row:
                            rows.append(row)
                if rows:
                    return rows, ""
        except json.JSONDecodeError:
            pass

    # 2. Try Delimited text (CSV / TSV)
    # Sniff delimiter
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return [], "The uploaded file is empty."

    sample = "\n".join(lines[:10])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = "\t" if "\t" in lines[0] else (";" if ";" in lines[0] else ",")

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    headers = None
    column_map = {}
    rows = []

    for raw_row in reader:
        if not raw_row or not any(c.strip() for c in raw_row):
            continue
        if headers is None:
            headers = raw_row
            for idx, h in enumerate(headers):
                canonical = _match_column(h)
                if canonical:
                    column_map[idx] = canonical
            continue

        row_dict = {}
        for idx, val in enumerate(raw_row):
            canonical = column_map.get(idx)
            if canonical:
                row_dict[canonical] = val.strip()

        if row_dict:
            rows.append(row_dict)

    if not column_map:
        return [], (
            "Could not recognize column headers. Please include headers like: "
            "'Medicine Name', 'Category', 'Quantity', 'Unit Price', 'Reorder Level'."
        )

    return rows, ""


def import_inventory_data(rows, user, default_branch=None, mode="update_or_add"):
    """
    Imports parsed rows and reflects changes to the database.
    mode can be:
      - 'update_or_add' (set exact stock and update/create medicine)
      - 'increment'     (add quantity to existing stock)
    Returns: summary dict
    """
    company = user.company
    if not company:
        return {
            "success": False,
            "message": "User is not associated with an active company.",
            "total": 0,
            "created_meds": 0,
            "updated_meds": 0,
            "created_stock": 0,
            "updated_stock": 0,
            "skipped": 0,
            "errors": [],
        }

    # Cache visible branches for fast lookup
    active_branches = list(Branch.objects.filter(company=company, is_active=True))
    branch_lookup = {b.branch_name.strip().lower(): b for b in active_branches}
    for b in active_branches:
        branch_lookup[str(b.branch_id)] = b

    created_meds = 0
    updated_meds = 0
    created_stock = 0
    updated_stock = 0
    skipped = 0
    errors = []

    with transaction.atomic():
        for line_num, row in enumerate(rows, start=1):
            med_name = row.get("medicine_name", "").strip()
            if not med_name:
                skipped += 1
                errors.append(f"Row {line_num}: Skipped because medicine name is missing.")
                continue

            generic_name = row.get("generic_name", "").strip() or med_name
            brand_name = row.get("brand_name", "").strip() or med_name
            category = row.get("category", "").strip() or "General"
            unit_of_measure = row.get("unit_of_measure", "").strip() or "tablets"
            unit_price = _parse_decimal(row.get("unit_price"), Decimal("0.00"))
            requires_prescription = _parse_bool(row.get("requires_prescription", False))
            quantity = _parse_int(row.get("quantity_on_hand"), 0)
            threshold = _parse_int(row.get("reorder_threshold"), 10)

            # 1. Resolve Target Branch
            row_branch_val = row.get("branch", "").strip().lower()
            target_branch = branch_lookup.get(row_branch_val) or default_branch or user.branch
            if not target_branch and active_branches:
                target_branch = active_branches[0]

            if not target_branch:
                skipped += 1
                errors.append(f"Row {line_num} ('{med_name}'): No active branch available for stock placement.")
                continue

            # 2. Get or Create Medicine
            medicine = Medicine.objects.filter(
                company=company,
                medicine_name__iexact=med_name,
            ).first()

            if medicine:
                # Update catalogue metadata if provided
                changed = False
                if row.get("generic_name") and medicine.generic_name != generic_name:
                    medicine.generic_name = generic_name
                    changed = True
                if row.get("brand_name") and medicine.brand_name != brand_name:
                    medicine.brand_name = brand_name
                    changed = True
                if row.get("category") and medicine.category != category:
                    medicine.category = category
                    changed = True
                if row.get("unit_of_measure") and medicine.unit_of_measure != unit_of_measure:
                    medicine.unit_of_measure = unit_of_measure
                    changed = True
                if row.get("unit_price") and medicine.unit_price != unit_price:
                    medicine.unit_price = unit_price
                    changed = True
                if changed:
                    medicine.save()
                    updated_meds += 1
            else:
                medicine = Medicine.objects.create(
                    company=company,
                    medicine_name=med_name,
                    generic_name=generic_name,
                    brand_name=brand_name,
                    category=category,
                    unit_of_measure=unit_of_measure,
                    unit_price=unit_price,
                    requires_prescription=requires_prescription,
                    is_active=True,
                )
                created_meds += 1

            # 3. Get or Create/Update Inventory Record
            inv_record = Inventory.objects.filter(
                branch=target_branch,
                medicine=medicine,
            ).first()

            if inv_record:
                if mode == "increment":
                    inv_record.quantity_on_hand += max(0, quantity)
                else:  # update_or_add / set
                    inv_record.quantity_on_hand = max(0, quantity)

                if row.get("reorder_threshold") is not None:
                    inv_record.reorder_threshold = max(0, threshold)
                inv_record.save()
                updated_stock += 1
            else:
                Inventory.objects.create(
                    branch=target_branch,
                    medicine=medicine,
                    quantity_on_hand=max(0, quantity),
                    reorder_threshold=max(0, threshold),
                )
                created_stock += 1

    return {
        "success": True,
        "total": len(rows),
        "created_meds": created_meds,
        "updated_meds": updated_meds,
        "created_stock": created_stock,
        "updated_stock": updated_stock,
        "skipped": skipped,
        "errors": errors[:5],  # Cap sample errors
    }

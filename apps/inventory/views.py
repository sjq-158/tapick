import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Subquery
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from apps.home.models import Inventory, Medicine
from apps.notifications.rules import (
    send_custom_branch_notification,
    send_stock_request,
    stock_status,
)
from apps.register.models import Branch

from .access import can_manage_catalogue, visible_branches, visible_medicines
from .forms import AddStockForm, AdjustStockForm, MedicineForm
from .importer import import_inventory_data, parse_file_content
from .reports import generate_inventory_csv, generate_inventory_pdf

OUT_Q = Q(quantity_on_hand__lte=0)
LOW_Q = Q(quantity_on_hand__gt=0, quantity_on_hand__lte=F("reorder_threshold"))
OK_Q = Q(quantity_on_hand__gt=0) & Q(quantity_on_hand__gt=F("reorder_threshold"))
STATUS_FILTERS = {"out": OUT_Q, "low": LOW_Q, "ok": OK_Q}


def first_error(form):
    field, errors = next(iter(form.errors.items()))
    prefix = "" if field == "__all__" else field.replace("_", " ").capitalize() + ": "
    return prefix + errors[0]


def attach_status(rows, user=None):
    """
    Annotates stock status and locates cross-branch availability.
    Computes exact distance to each stocking branch, sorting nearest-first.
    """
    needy = []
    user_branch = getattr(user, "branch", None) if user else None
    for row in rows:
        row.status = stock_status(row.quantity_on_hand, row.reorder_threshold)
        row.elsewhere = []
        row.nearest_branch = None
        row.nearest_distance = None
        row.nearest_qty = 0
        if row.status != "ok":
            needy.append(row)
    if not needy:
        return
    pool = (
        Inventory.objects.filter(
            medicine_id__in={r.medicine_id for r in needy},
            branch__company_id__in={r.branch.company_id for r in needy},
            branch__is_active=True,
            quantity_on_hand__gt=0,
        )
        .select_related("branch")
        .order_by("-quantity_on_hand")
    )
    by_medicine = {}
    for item in pool:
        by_medicine.setdefault(item.medicine_id, []).append(item)
    for row in needy:
        sources = [
            item for item in by_medicine.get(row.medicine_id, [])
            if item.branch_id != row.branch_id and item.branch.company_id == row.branch.company_id
        ]
        # Calculate distance from the local branch to each stocking branch
        origin = row.branch or user_branch
        for s in sources:
            s.distance_km = origin.distance_to(s.branch) if origin else 0.0

        # Sort sources nearest first (ascending distance)
        sources.sort(key=lambda s: (s.distance_km if s.distance_km is not None else 9999, -s.quantity_on_hand))
        row.elsewhere = sources
        if sources:
            row.nearest_branch = sources[0].branch
            row.nearest_distance = sources[0].distance_km
            row.nearest_qty = sources[0].quantity_on_hand


def get_filtered_inventory(request):
    """Reusable helper to filter inventory based on GET parameters."""
    user = request.user
    branches = list(visible_branches(user).order_by("branch_name"))
    base = Inventory.objects.filter(branch__in=branches, medicine__is_active=True).select_related("medicine", "branch")

    counts = base.aggregate(
        total=Count("pk"),
        out=Count("pk", filter=OUT_Q),
        low=Count("pk", filter=LOW_Q),
    )
    counts["ok"] = counts["total"] - counts["out"] - counts["low"]

    rows = base
    q = request.GET.get("q", "").strip()
    if q:
        rows = rows.filter(
            Q(medicine__medicine_name__icontains=q)
            | Q(medicine__generic_name__icontains=q)
            | Q(medicine__brand_name__icontains=q)
            | Q(medicine__category__icontains=q)
        )
    branch_id = request.GET.get("branch", "")
    selected_branch = None
    if branch_id.isdigit() and int(branch_id) in {b.branch_id for b in branches}:
        rows = rows.filter(branch_id=int(branch_id))
        selected_branch = next((b for b in branches if b.branch_id == int(branch_id)), None)
    else:
        branch_id = ""

    status = request.GET.get("status", "")
    if status == "subquery":
        # Subquery filter: selects medicines with branch stock at or below the reorder threshold.
        critical_ids = Inventory.objects.filter(branch__in=branches, quantity_on_hand__lte=F("reorder_threshold")).values("medicine_id")
        rows = rows.filter(medicine_id__in=Subquery(critical_ids))
    elif status in STATUS_FILTERS:
        rows = rows.filter(STATUS_FILTERS[status])
    else:
        status = ""

    scope_label = selected_branch.branch_name if selected_branch else (
        branches[0].branch_name if len(branches) == 1 else f"All branches ({len(branches)})"
    )

    return rows.order_by("medicine__medicine_name", "branch__branch_name"), counts, branches, scope_label, q, branch_id, status


@method_decorator(login_required, name="dispatch")
class InventoryScreen(View):
    def get(self, request):
        user = request.user
        rows, counts, branches, scope_label, q, branch_id, status = get_filtered_inventory(request)

        page = Paginator(rows, 15).get_page(request.GET.get("page"))
        page_rows = list(page.object_list)
        attach_status(page_rows, user=user)

        params = request.GET.copy()
        params.pop("page", None)

        # Prepare Map Branches Data with coordinates & distance for Leaflet
        user_branch = user.branch or (branches[0] if branches else None)
        branches_json = []
        for b in branches:
            lat, lng = b.coordinates
            dist = user_branch.distance_to(b) if user_branch else 0.0
            branches_json.append({
                "id": b.branch_id,
                "name": b.branch_name,
                "address": f"{b.street_address}, {b.city}",
                "phone": b.branch_phone,
                "lat": lat,
                "lng": lng,
                "is_user_branch": bool(user_branch and b.branch_id == user_branch.branch_id),
                "distance_km": dist,
            })

        return render(request, "inventory/inventory.html", {
            "page": page,
            "rows": page_rows,
            "counts": counts,
            "branches": branches,
            "branches_json": json.dumps(branches_json),
            "medicines": visible_medicines(user).order_by("medicine_name"),
            "scope_count": len(branches),
            "scope_label": scope_label,
            "can_manage_catalogue": can_manage_catalogue(user),
            "is_admin": user.role == "admin",
            "q": q,
            "branch_id": branch_id,
            "status": status,
            "querystring": params.urlencode(),
            "user_branch": user_branch,
        })


@login_required
@require_POST
def add_stock(request):
    form = AddStockForm(request.POST, user=request.user)
    if not form.is_valid():
        messages.error(request, first_error(form))
        return redirect("inventory:list")

    data = form.cleaned_data
    if Inventory.objects.filter(branch=data["branch"], medicine=data["medicine"]).exists():
        messages.error(request, f"{data['medicine']} is already tracked at {data['branch']}. Use Update instead.")
        return redirect("inventory:list")

    Inventory.objects.create(
        branch=data["branch"],
        medicine=data["medicine"],
        quantity_on_hand=data["quantity_on_hand"],
        reorder_threshold=data["reorder_threshold"],
    )
    messages.success(request, f"{data['medicine']} added to {data['branch']}.")
    return redirect("inventory:list")


@login_required
@require_POST
def update_stock(request, pk):
    form = AdjustStockForm(request.POST)
    if not form.is_valid():
        messages.error(request, first_error(form))
        return redirect("inventory:list")

    data = form.cleaned_data
    with transaction.atomic():
        row = get_object_or_404(
            Inventory.objects.select_for_update().filter(branch__in=visible_branches(request.user)), pk=pk
        )
        quantity = {
            "set": data["amount"],
            "add": row.quantity_on_hand + data["amount"],
            "remove": row.quantity_on_hand - data["amount"],
        }[data["action"]]
        if quantity < 0:
            messages.error(request, f"Cannot remove {data['amount']}: only {row.quantity_on_hand} on hand.")
            return redirect("inventory:list")

        row.quantity_on_hand = quantity
        if data["reorder_threshold"] is not None:
            row.reorder_threshold = data["reorder_threshold"]
        row.save()

    messages.success(request, f"{row.medicine} at {row.branch} is now {row.quantity_on_hand} {row.medicine.unit_of_measure}.")
    return redirect("inventory:list")


@login_required
@require_POST
def request_stock(request, pk):
    row = get_object_or_404(
        Inventory.objects.select_related("medicine", "branch").filter(branch__in=visible_branches(request.user)), pk=pk
    )
    if stock_status(row.quantity_on_hand, row.reorder_threshold) == "ok":
        messages.info(request, f"{row.medicine} is above its reorder level. No request needed.")
        return redirect("inventory:list")

    result, count = send_stock_request(row, request.user)
    if result == "sent":
        messages.success(request, f"Stock request sent to {count} staff member{'s' if count != 1 else ''} at branches that have {row.medicine}.")
    elif result == "skipped":
        messages.info(request, "A request for this medicine was already sent in the last 10 minutes.")
    else:
        messages.warning(request, f"No other branch currently has {row.medicine} in stock.")
    return redirect("inventory:list")


@login_required
@require_POST
def send_branch_notice(request):
    """
    Directly sends a cross-branch notification / stock request to another branch.
    Alerts all active pharmacists at that branch and company head pharmacists.
    """
    target_branch_id = request.POST.get("target_branch")
    medicine_id = request.POST.get("medicine")
    quantity = request.POST.get("quantity")
    urgency = request.POST.get("urgency", "normal")
    note = request.POST.get("note", "").strip()

    if not target_branch_id:
        messages.error(request, "Please select a target branch.")
        return redirect("inventory:list")

    target_branch = get_object_or_404(
        Branch.objects.filter(company=request.user.company, is_active=True), pk=target_branch_id
    )

    medicine = None
    if medicine_id and medicine_id.isdigit():
        medicine = Medicine.objects.filter(company=request.user.company, pk=int(medicine_id)).first()

    status, count = send_custom_branch_notification(
        target_branch=target_branch,
        sender_user=request.user,
        medicine=medicine,
        quantity=quantity,
        note=note,
        urgency=urgency,
    )

    if status == "sent":
        messages.success(
            request,
            f"Notification successfully delivered to {target_branch.branch_name}! "
            f"Reflected on the screens of {count} employee(s) (head pharmacist and pharmacists at {target_branch.branch_name})."
        )
    elif status == "no_recipients":
        messages.warning(
            request,
            f"Notification recorded, but no active pharmacists are currently assigned to {target_branch.branch_name}."
        )
    else:
        messages.error(request, "Failed to send notification.")

    return redirect("inventory:list")


@login_required
@require_POST
def add_medicine(request):
    if not can_manage_catalogue(request.user):
        messages.error(request, "Only a head pharmacist can add medicines to the catalogue.")
        return redirect("inventory:list")

    form = MedicineForm(request.POST)
    if not form.is_valid():
        messages.error(request, first_error(form))
        return redirect("inventory:list")

    medicine = form.save(commit=False)
    medicine.company_id = request.user.company_id
    medicine.save()
    messages.success(request, f"{medicine} added to the catalogue. You can now add stock for it.")
    return redirect("inventory:list")


# File upload processing and inventory content import.
@login_required
@require_POST
def upload_file(request):
    """
    Accepts an uploaded file (CSV, TSV, JSON), understands columns,
    and reflects changes to medicines and branch stock levels.
    """
    uploaded = request.FILES.get("file")
    if not uploaded:
        messages.error(request, "Please choose a file to upload (.csv, .tsv, .txt, or .json).")
        return redirect("inventory:list")

    if uploaded.size > 10 * 1024 * 1024:
        messages.error(request, "File size exceeds 10MB limit.")
        return redirect("inventory:list")

    target_branch = None
    branch_val = request.POST.get("target_branch")
    if branch_val and branch_val.isdigit():
        target_branch = Branch.objects.filter(
            pk=int(branch_val), company=request.user.company, is_active=True
        ).first()

    mode = request.POST.get("import_mode", "update_or_add")
    if mode not in ("update_or_add", "increment"):
        mode = "update_or_add"

    rows, err = parse_file_content(uploaded, uploaded.name)
    if err:
        messages.error(request, f"Could not read '{uploaded.name}': {err}")
        return redirect("inventory:list")

    if not rows:
        messages.warning(request, f"File '{uploaded.name}' contains no readable inventory rows.")
        return redirect("inventory:list")

    result = import_inventory_data(rows, request.user, default_branch=target_branch, mode=mode)
    if not result.get("success"):
        messages.error(request, f"Import failed: {result.get('message', 'Unknown error')}")
        return redirect("inventory:list")

    parts = []
    if result["created_meds"]:
        parts.append(f"{result['created_meds']} new medicine(s) catalogued")
    if result["updated_meds"]:
        parts.append(f"{result['updated_meds']} medicine(s) updated")
    if result["created_stock"]:
        parts.append(f"{result['created_stock']} new stock record(s) created")
    if result["updated_stock"]:
        parts.append(f"{result['updated_stock']} stock level(s) updated")

    action_summary = ", ".join(parts) if parts else "No changes detected"
    full_msg = f"File '{uploaded.name}' processed successfully ({result['total']} rows understood): {action_summary}."
    if result.get("skipped"):
        full_msg += f" Note: {result['skipped']} row(s) were skipped due to missing medicine names."

    messages.success(request, full_msg)

    if result.get("errors"):
        for err_line in result["errors"]:
            messages.warning(request, err_line)

    return redirect("inventory:list")


@login_required
def download_template(request):
    """Provides a sample CSV template for users to format their inventory data."""
    sample_csv = (
        "medicine_name,generic_name,brand_name,category,unit_of_measure,unit_price,quantity_on_hand,reorder_threshold,branch,requires_prescription\r\n"
        "Paracetamol 500 mg,Paracetamol,Biogesic,Pain Relief,tablets,6.50,150,25,,No\r\n"
        "Amoxicillin 500 mg,Amoxicillin,Amoxil,Antibiotics,capsules,12.00,90,20,,Yes\r\n"
        "Cetirizine 10 mg,Cetirizine,Virlix,Antihistamine,tablets,8.75,110,15,,No\r\n"
        "Mefenamic Acid 500 mg,Mefenamic Acid,Ponstan,Pain Relief,capsules,14.50,45,10,,Yes\r\n"
        "Omeprazole 20 mg,Omeprazole,Prilosec,Gastrointestinal,capsules,18.00,60,15,,Yes\r\n"
        "Losartan 50 mg,Losartan,Cozaar,Cardiovascular,tablets,16.50,85,20,,Yes\r\n"
        "Ibuprofen 400 mg,Ibuprofen,Advil,Pain Relief,tablets,9.00,0,15,,No\r\n"
    )
    response = HttpResponse(sample_csv.encode("utf-8-sig"), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="tapick_inventory_template.csv"'
    return response


# Export inventory summaries in CSV and PDF formats.
@login_required
def export_csv(request):
    """Exports inventory data and summary metrics as a UTF-8 BOM CSV spreadsheet."""
    rows, counts, branches, scope_label, q, branch_id, status = get_filtered_inventory(request)
    csv_bytes = generate_inventory_csv(rows, counts, request.user, scope_label=scope_label)
    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"tapick_inventory_summary_{timestamp}.csv"
    response = HttpResponse(csv_bytes, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def export_pdf(request):
    """Exports an executive inventory summary report as a formatted PDF."""
    rows, counts, branches, scope_label, q, branch_id, status = get_filtered_inventory(request)

    filter_parts = []
    if q:
        filter_parts.append(f'Search: "{q}"')
    if branch_id:
        filter_parts.append(f"Branch: {scope_label}")
    if status:
        filter_parts.append(f"Status: {status.capitalize()}")
    filters_desc = " | ".join(filter_parts) if filter_parts else "All records"

    pdf_bytes = generate_inventory_pdf(
        rows, counts, request.user, scope_label=scope_label, filters_desc=filters_desc
    )
    timestamp = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"tapick_inventory_summary_{timestamp}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# Live status polling and cross-branch stock locator endpoints.
@login_required
def live_status(request):
    """
    Real-time 5-second polling endpoint:
    Returns live inventory KPI counts system-wide within 5 seconds.
    """
    rows, counts, branches, scope_label, q, branch_id, status = get_filtered_inventory(request)
    return JsonResponse({
        "timestamp": timezone.now().strftime("%I:%M:%S %p"),
        "total": counts.get("total", 0),
        "ok": counts.get("ok", 0),
        "low": counts.get("low", 0),
        "out": counts.get("out", 0),
    })


@login_required
def locate_medicine(request):
    """
    Real-time Cross-Branch Stock Locator:
    Searches available stock across other branches, calculates distance,
    and identifies the nearest branch where medicine is available.
    """
    user = request.user
    user_branch = user.branch
    q = request.GET.get("q", "").strip()
    med_id = request.GET.get("id")

    items = Inventory.objects.filter(
        medicine__company_id=user.company_id,
        branch__company_id=user.company_id,
        branch__is_active=True,
        quantity_on_hand__gt=0,
    ).select_related("medicine", "branch")

    if med_id and med_id.isdigit():
        items = items.filter(medicine_id=int(med_id))
    elif q:
        items = items.filter(
            Q(medicine__medicine_name__icontains=q)
            | Q(medicine__generic_name__icontains=q)
            | Q(medicine__brand_name__icontains=q)
        )

    results = []
    for item in items:
        lat, lng = item.branch.coordinates
        dist = user_branch.distance_to(item.branch) if user_branch else 0.0
        results.append({
            "medicine_id": item.medicine_id,
            "medicine_name": item.medicine.medicine_name,
            "unit": item.medicine.unit_of_measure,
            "branch_id": item.branch_id,
            "branch_name": item.branch.branch_name,
            "branch_address": f"{item.branch.street_address}, {item.branch.city}",
            "branch_phone": item.branch.branch_phone,
            "quantity": item.quantity_on_hand,
            "reorder_threshold": item.reorder_threshold,
            "lat": lat,
            "lng": lng,
            "distance_km": dist,
            "is_my_branch": bool(user_branch and item.branch_id == user_branch.branch_id),
        })

    results.sort(key=lambda r: (r["distance_km"] if r["distance_km"] is not None else 9999, -r["quantity"]))

    return JsonResponse({
        "count": len(results),
        "user_branch": {
            "name": user_branch.branch_name if user_branch else "All Branches",
            "lat": user_branch.coordinates[0] if user_branch else 10.3157,
            "lng": user_branch.coordinates[1] if user_branch else 123.8854,
        } if user_branch else None,
        "results": results,
    })


@login_required
@require_POST
def send_branch_notice(request):
    """
    Sends a cross-branch notification/stock inquiry to a target branch.
    Notifies all pharmacists at target branch and head pharmacists.
    Supports both JSON AJAX requests and regular HTML form submissions.
    """
    is_ajax = (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in (request.content_type or "")
    )
    if is_ajax and request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            payload = request.POST
    else:
        payload = request.POST

    target_branch_id = payload.get("target_branch_id") or payload.get("branch_id")
    if not target_branch_id:
        if is_ajax:
            return JsonResponse({"ok": False, "error": "Target branch is required."}, status=400)
        messages.error(request, "Target branch is required.")
        return redirect("inventory:list")

    target_branch = get_object_or_404(
        Branch,
        branch_id=target_branch_id,
        company_id=request.user.company_id,
    )

    medicine = None
    med_id = payload.get("medicine_id")
    if med_id:
        medicine = Medicine.objects.filter(
            medicine_id=med_id,
            company_id=request.user.company_id,
        ).first()

    quantity = payload.get("quantity")
    if quantity:
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = None

    urgency = payload.get("urgency", "normal")
    note = payload.get("note", "").strip()

    status_code, count = send_custom_branch_notification(
        target_branch=target_branch,
        sender_user=request.user,
        medicine=medicine,
        quantity=quantity,
        note=note,
        urgency=urgency,
    )

    if status_code == "no_recipients":
        msg = f"No active staff found at {target_branch.branch_name} to receive notification."
        if is_ajax:
            return JsonResponse({"ok": False, "error": msg}, status=404)
        messages.warning(request, msg)
    else:
        msg = f"Notification sent to {target_branch.branch_name} ({count} staff notified)."
        if is_ajax:
            return JsonResponse({"ok": True, "message": msg, "recipients_count": count})
        messages.success(request, msg)

    return redirect("inventory:list")


@login_required
def reorder_analysis(request):
    """
    Performs multi-branch stock inventory auditing and identifies medicines
    requiring reorder based on branch threshold limits.
    Combines records across related tables using select_related() and executes
    nested threshold filtering using Subquery().
    """
    user = request.user
    branches = visible_branches(user)

    # Combines inventory records with medicine and branch details using SQL JOIN.
    join_queryset = (
        Inventory.objects.filter(branch__in=branches, medicine__is_active=True)
        .select_related("medicine", "branch")
        .order_by("medicine__medicine_name", "branch__branch_name")
    )
    join_sql = str(join_queryset.query)
    join_samples = list(join_queryset[:12])

    # Identifies medicines whose stock is at or below reorder threshold using SQL SUBQUERY.
    inner_query = (
        Inventory.objects.filter(
            branch__in=branches,
            quantity_on_hand__lte=F("reorder_threshold"),
        ).values("medicine_id")
    )
    inner_sql = str(inner_query.query)

    subquery_queryset = (
        Medicine.objects.filter(
            medicine_id__in=Subquery(inner_query),
            is_active=True,
        )
        .order_by("medicine_name")
    )
    subquery_sql = str(subquery_queryset.query)
    subquery_samples = list(subquery_queryset[:12])

    # Prints generated SQL queries to console for database inspection.
    print("[SQL Audit] Inventory Multi-Branch Join (select_related):")
    print(join_sql)
    print("[SQL Audit] Reorder Threshold Subquery (Subquery):")
    print(subquery_sql)

    return render(
        request,
        "inventory/reorder_analysis.html",
        {
            "join_samples": join_samples,
            "join_sql": join_sql,
            "subquery_samples": subquery_samples,
            "subquery_sql": subquery_sql,
            "inner_sql": inner_sql,
            "join_count": join_queryset.count(),
            "subquery_count": subquery_queryset.count(),
        },
    )



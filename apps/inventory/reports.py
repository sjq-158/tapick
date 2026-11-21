import io
import re
from datetime import datetime
from decimal import Decimal


def _escape_pdf_text(text):
    """Escape special characters for PDF literal text strings in Type 1 fonts."""
    if text is None:
        return ""
    s = str(text)
    # Replace non-ASCII / Unicode currency with ASCII standard
    s = s.replace("₱", "Php ").replace("—", "-").replace("–", "-")
    s = s.replace("·", "-").replace("•", "-")
    # Clean out any characters above 127 to keep 100% standard Type 1 compatibility
    s = "".join(c if ord(c) < 128 else " " for c in s)
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return s


class PDFCanvas:
    """A lightweight, zero-dependency PDF 1.4 generator."""

    def __init__(self, page_width=842, page_height=595):
        self.width = page_width
        self.height = page_height
        self.pages = []
        self.current_stream = io.StringIO()
        self.current_page_num = 0

    def new_page(self):
        if self.current_page_num > 0:
            self.pages.append(self.current_stream.getvalue())
            self.current_stream = io.StringIO()
        self.current_page_num += 1

    def set_fill_color(self, r, g, b):
        self.current_stream.write(f"{r:.3f} {g:.3f} {b:.3f} rg\n")

    def set_stroke_color(self, r, g, b):
        self.current_stream.write(f"{r:.3f} {g:.3f} {b:.3f} RG\n")

    def set_line_width(self, w):
        self.current_stream.write(f"{w:.2f} w\n")

    def rect(self, x, y, w, h, fill=True, stroke=False):
        op = "B" if (fill and stroke) else ("f" if fill else "S")
        self.current_stream.write(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}\n")

    def line(self, x1, y1, x2, y2):
        self.current_stream.write(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S\n")

    def draw_text(self, text, x, y, font="F1", size=10, r=0.1, g=0.1, b=0.1):
        clean = _escape_pdf_text(text)
        self.set_fill_color(r, g, b)
        self.current_stream.write(
            f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({clean}) Tj ET\n"
        )

    def draw_text_right(self, text, right_x, y, font="F1", size=10, r=0.1, g=0.1, b=0.1):
        """Right-align text using approximate character width calculation."""
        clean = _escape_pdf_text(text)
        # Average character width ratio for Helvetica: ~0.52 of font size
        est_width = len(clean) * (size * 0.52)
        x = max(0.0, right_x - est_width)
        self.draw_text(clean, x, y, font=font, size=size, r=r, g=g, b=b)

    def finish(self):
        if self.current_page_num > 0:
            self.pages.append(self.current_stream.getvalue())

        total_pages = len(self.pages)
        if total_pages == 0:
            self.new_page()
            self.pages.append(self.current_stream.getvalue())
            total_pages = 1

        # Build PDF objects
        # Object 1: Catalog
        # Object 2: Pages
        # Object 3..2+N: Page objects
        # Object 3+N: Font F1 (Helvetica)
        # Object 4+N: Font F2 (Helvetica-Bold)
        # Object 5+N..: Content streams
        out = io.BytesIO()
        offsets = {}

        def write_obj(num, content_bytes):
            offsets[num] = out.tell()
            out.write(f"{num} 0 obj\n".encode("ascii"))
            out.write(content_bytes)
            out.write(b"\nendobj\n")

        out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        font1_num = 3 + total_pages
        font2_num = font1_num + 1

        # Catalog
        write_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")

        # Page object numbers: 3 to 2+total_pages
        page_nums = list(range(3, 3 + total_pages))
        kids_str = " ".join(f"{p} 0 R" for p in page_nums)
        write_obj(2, f"<< /Type /Pages /Kids [{kids_str}] /Count {total_pages} >>".encode("ascii"))

        # Fonts
        write_obj(font1_num, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        write_obj(font2_num, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        stream_start_num = font2_num + 1

        for idx, page_content in enumerate(self.pages):
            page_obj_num = page_nums[idx]
            stream_obj_num = stream_start_num + idx

            # Append footer with total pages known
            footer_str = (
                f"BT /F1 8 Tf 36 22 Td ({_escape_pdf_text('Tapick Pharmacy Management - Confidential')}) Tj ET\n"
                f"BT /F1 8 Tf {self.width - 95:.2f} 22 Td ({_escape_pdf_text(f'Page {idx + 1} of {total_pages}')}) Tj ET\n"
            )
            full_stream_text = page_content + footer_str
            stream_bytes = full_stream_text.encode("latin-1", errors="replace")

            # Page object
            page_dict = (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width} {self.height}] "
                f"/Resources << /Font << /F1 {font1_num} 0 R /F2 {font2_num} 0 R >> >> "
                f"/Contents {stream_obj_num} 0 R >>"
            )
            write_obj(page_obj_num, page_dict.encode("ascii"))

            # Content stream object
            stream_dict = f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii") + stream_bytes + b"\nendstream"
            write_obj(stream_obj_num, stream_dict)

        # Cross reference table
        total_objs = stream_start_num + total_pages
        xref_offset = out.tell()
        out.write(f"xref\n0 {total_objs}\n".encode("ascii"))
        out.write(b"0000000000 65535 f \n")
        for num in range(1, total_objs):
            pos = offsets.get(num, 0)
            out.write(f"{pos:010d} 00000 n \n".encode("ascii"))

        out.write(
            f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
        )

        return out.getvalue()


def generate_inventory_pdf(inventory_qs, counts, user, scope_label="All Branches", filters_desc="None"):
    """
    Renders an elegant, professional A4 landscape inventory report PDF.
    """
    pdf = PDFCanvas(page_width=842, page_height=595)

    margin_x = 36
    margin_top = 40
    usable_width = 842 - (margin_x * 2)  # 770 pt

    # Calculate valuation
    total_val = Decimal("0.00")
    for row in inventory_qs:
        unit_price = getattr(row.medicine, "unit_price", Decimal("0.00")) or Decimal("0.00")
        qty = row.quantity_on_hand or 0
        total_val += (unit_price * qty)

    # Columns: (label, width, is_right)
    columns = [
        ("Medicine", 170, False),
        ("Generic Name", 130, False),
        ("Category", 95, False),
        ("Branch", 105, False),
        ("On Hand", 65, True),
        ("Reorder", 65, True),
        ("Status", 70, False),
        ("Price (Php)", 70, True),
    ]

    def draw_page_header():
        # Top banner
        pdf.draw_text("TAPICK", margin_x, 560, font="F2", size=18, r=0.12, g=0.45, b=0.40)
        pdf.draw_text("Inventory Summary Report", margin_x + 85, 560, font="F2", size=14, r=0.15, g=0.15, b=0.15)
        pdf.draw_text(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | User: {user.email} | Scope: {scope_label}",
            margin_x, 544, font="F1", size=8.5, r=0.45, g=0.45, b=0.45
        )
        pdf.set_stroke_color(0.80, 0.85, 0.84)
        pdf.set_line_width(1)
        pdf.line(margin_x, 536, margin_x + usable_width, 536)

    def draw_kpi_cards():
        # 5 Stat blocks
        card_w = (usable_width - 32) / 5
        card_h = 42
        y = 484

        stats = [
            ("Tracked Items", str(counts.get("total", 0)), (0.95, 0.97, 0.97), (0.2, 0.2, 0.2)),
            ("Healthy Stock", str(counts.get("ok", 0)), (0.91, 0.96, 0.92), (0.15, 0.55, 0.25)),
            ("Low Stock", str(counts.get("low", 0)), (0.99, 0.96, 0.90), (0.75, 0.45, 0.05)),
            ("Out of Stock", str(counts.get("out", 0)), (0.99, 0.92, 0.92), (0.75, 0.15, 0.15)),
            ("Est. Valuation", f"Php {total_val:,.2f}", (0.93, 0.96, 0.98), (0.1, 0.35, 0.65)),
        ]

        for i, (label, val, bg, fg) in enumerate(stats):
            x = margin_x + (i * (card_w + 8))
            pdf.set_fill_color(*bg)
            pdf.rect(x, y, card_w, card_h, fill=True, stroke=False)
            pdf.draw_text(label, x + 8, y + 26, font="F1", size=7.5, r=0.4, g=0.4, b=0.4)
            pdf.draw_text(val, x + 8, y + 10, font="F2", size=11, r=fg[0], g=fg[1], b=fg[2])

    def draw_table_header(y_pos):
        # Table Header Background
        pdf.set_fill_color(0.18, 0.22, 0.21)
        pdf.rect(margin_x, y_pos, usable_width, 20, fill=True, stroke=False)

        cur_x = margin_x
        for label, width, is_right in columns:
            if is_right:
                pdf.draw_text_right(label, cur_x + width - 6, y_pos + 6, font="F2", size=8, r=1.0, g=1.0, b=1.0)
            else:
                pdf.draw_text(label, cur_x + 6, y_pos + 6, font="F2", size=8, r=1.0, g=1.0, b=1.0)
            cur_x += width

    # First page
    pdf.new_page()
    draw_page_header()
    draw_kpi_cards()

    cur_y = 450
    draw_table_header(cur_y)
    cur_y -= 18

    # Print rows
    for row_idx, item in enumerate(inventory_qs):
        if cur_y < 45:
            # Need new page
            pdf.new_page()
            draw_page_header()
            cur_y = 505
            draw_table_header(cur_y)
            cur_y -= 18

        # Row background (zebra striping)
        bg = (0.97, 0.98, 0.98) if row_idx % 2 == 1 else (1.0, 1.0, 1.0)
        pdf.set_fill_color(*bg)
        pdf.rect(margin_x, cur_y, usable_width, 17, fill=True, stroke=False)

        # Bottom row line
        pdf.set_stroke_color(0.90, 0.92, 0.92)
        pdf.set_line_width(0.5)
        pdf.line(margin_x, cur_y, margin_x + usable_width, cur_y)

        # Status text and color
        qty = item.quantity_on_hand
        thresh = item.reorder_threshold
        if qty <= 0:
            status_txt = "Out of stock"
            st_color = (0.75, 0.15, 0.15)
        elif qty <= thresh:
            status_txt = "Low stock"
            st_color = (0.75, 0.45, 0.05)
        else:
            status_txt = "Healthy"
            st_color = (0.15, 0.55, 0.25)

        med = item.medicine
        unit_price = getattr(med, "unit_price", Decimal("0.00")) or Decimal("0.00")
        price_str = f"{unit_price:.2f}"

        # Truncate strings to prevent overlap
        name_txt = (med.medicine_name[:24] + "...") if len(med.medicine_name) > 27 else med.medicine_name
        gen_txt = (med.generic_name[:18] + "...") if len(med.generic_name) > 21 else med.generic_name
        cat_txt = (med.category[:13] + "...") if len(med.category) > 15 else med.category
        branch_txt = (item.branch.branch_name[:15] + "...") if len(item.branch.branch_name) > 17 else item.branch.branch_name

        values = [
            (name_txt, False, (0.15, 0.15, 0.15), "F2"),
            (gen_txt, False, (0.40, 0.40, 0.40), "F1"),
            (cat_txt, False, (0.40, 0.40, 0.40), "F1"),
            (branch_txt, False, (0.35, 0.35, 0.35), "F1"),
            (f"{qty} {med.unit_of_measure}", True, (0.15, 0.15, 0.15), "F2"),
            (str(thresh), True, (0.45, 0.45, 0.45), "F1"),
            (status_txt, False, st_color, "F2"),
            (price_str, True, (0.15, 0.15, 0.15), "F1"),
        ]

        cur_x = margin_x
        for i, (val, is_right, fg, font_type) in enumerate(values):
            col_w = columns[i][1]
            if is_right:
                pdf.draw_text_right(val, cur_x + col_w - 6, cur_y + 4.5, font=font_type, size=7.5, r=fg[0], g=fg[1], b=fg[2])
            else:
                pdf.draw_text(val, cur_x + 6, cur_y + 4.5, font=font_type, size=7.5, r=fg[0], g=fg[1], b=fg[2])
            cur_x += col_w

        cur_y -= 17

    return pdf.finish()


def generate_inventory_csv(inventory_qs, counts, user, scope_label="All Branches"):
    """
    Generates a full-detail CSV export of the inventory data with UTF-8 BOM.
    """
    out = io.StringIO()
    # Write UTF-8 BOM so Microsoft Excel automatically recognizes encoding
    out.write("\ufeff")
    writer = csv.writer(out)

    # 1. Report Metadata
    writer.writerow(["Tapick - Inventory Summary Report"])
    writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Generated By", user.email])
    writer.writerow(["Scope", scope_label])
    writer.writerow([])

    # 2. Executive KPI Summary Block
    writer.writerow(["SUMMARY METRICS"])
    writer.writerow(["Total Tracked Items", counts.get("total", 0)])
    writer.writerow(["Healthy Stock Items", counts.get("ok", 0)])
    writer.writerow(["Low Stock Items", counts.get("low", 0)])
    writer.writerow(["Out of Stock Items", counts.get("out", 0)])

    total_units = sum(r.quantity_on_hand for r in inventory_qs)
    total_val = sum((r.medicine.unit_price or Decimal("0.00")) * r.quantity_on_hand for r in inventory_qs)
    writer.writerow(["Total Units on Hand", total_units])
    writer.writerow(["Total Inventory Valuation (PHP)", f"{total_val:.2f}"])
    writer.writerow([])

    # 3. Data Table Headers
    writer.writerow([
        "Medicine ID",
        "Medicine Name",
        "Generic Name",
        "Brand Name",
        "Category",
        "Unit of Measure",
        "Unit Price (PHP)",
        "Branch ID",
        "Branch Name",
        "Quantity On Hand",
        "Reorder Threshold",
        "Stock Status",
        "Total Value (PHP)",
        "Requires Prescription",
        "Last Updated",
    ])

    # 4. Data Rows
    for row in inventory_qs:
        med = row.medicine
        price = med.unit_price or Decimal("0.00")
        qty = row.quantity_on_hand
        val = price * qty

        if qty <= 0:
            status = "Out of Stock"
        elif qty <= row.reorder_threshold:
            status = "Low Stock"
        else:
            status = "Healthy"

        writer.writerow([
            med.medicine_id,
            med.medicine_name,
            med.generic_name,
            med.brand_name,
            med.category,
            med.unit_of_measure,
            f"{price:.2f}",
            row.branch_id,
            row.branch.branch_name,
            qty,
            row.reorder_threshold,
            status,
            f"{val:.2f}",
            "Yes" if med.requires_prescription else "No",
            row.last_updated.strftime("%Y-%m-%d %H:%M") if row.last_updated else "",
        ])

    return out.getvalue().encode("utf-8-sig")

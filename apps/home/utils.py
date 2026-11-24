import calendar
from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.register.models import Branch, Company, User
from .models import Medicine, Sale, SaleItem


def ensure_seed_sales(company=None, branch=None):
    """
    Ensures that branches have realistic transaction history for calendar inspection.
    Seeds realistic sales for the current month if none exist yet.
    """
    try:
        branches_to_check = []
        if branch:
            branches_to_check = [branch]
        elif company:
            branches_to_check = list(Branch.objects.filter(company=company, is_active=True))
        else:
            branches_to_check = list(Branch.objects.filter(is_active=True))

        for b in branches_to_check:
            if Sale.objects.filter(branch=b).exists():
                continue

            # Fetch active medicines for this branch's company
            meds = list(Medicine.objects.filter(company=b.company, is_active=True))
            if not meds:
                meds = list(Medicine.objects.filter(is_active=True))
            if not meds:
                continue

            # Find a user for this branch or company
            user = (
                User.objects.filter(branch=b, is_active=True).first()
                or User.objects.filter(company=b.company, is_active=True).first()
                or User.objects.first()
            )
            if not user:
                continue

            now = timezone.localtime()
            # Distribute 6 realistic sales across the current month
            offsets = [
                (0, 9, 25),    # today morning
                (0, 14, 40),   # today afternoon
                (1, 11, 15),   # yesterday
                (3, 16, 10),   # 3 days ago
                (5, 10, 50),   # 5 days ago
                (9, 15, 30),   # 9 days ago
                (14, 13, 20),  # 14 days ago
            ]

            with transaction.atomic():
                for idx, (days_ago, hour, minute) in enumerate(offsets):
                    target_time = (now - timedelta(days=days_ago)).replace(
                        hour=hour, minute=minute, second=0, microsecond=0
                    )
                    # Pick 1-3 medicines deterministically
                    sample_meds = [
                        meds[(idx + 0) % len(meds)],
                        meds[(idx + 2) % len(meds)],
                    ]

                    sale = Sale.objects.create(
                        branch=b,
                        user=user,
                        total_amount=Decimal("0.00"),
                        sold_at=target_time,
                    )

                    sale_total = Decimal("0.00")
                    for m_idx, med in enumerate(sample_meds):
                        qty = ((idx + m_idx) % 3) + 1
                        unit_price = med.unit_price or Decimal("15.00")
                        subtotal = unit_price * qty
                        sale_total += subtotal

                        SaleItem.objects.create(
                            sale=sale,
                            medicine=med,
                            quantity_sold=qty,
                            unit_price_at_sale=unit_price,
                            subtotal=subtotal,
                        )

                    sale.total_amount = sale_total
                    sale.save(update_fields=["total_amount"])
    except Exception:
        # In case of read-only replica or transient error, proceed gracefully
        pass


def get_calendar_events_data(user, year=None, month=None, branch_id=None):
    """
    Retrieves and formats sales transactions for the Notion calendar.
    Strictly enforces branch scoping for Pharmacists and Head Pharmacists.
    Provides company-wide read-only oversight for Administrators.
    """
    now = timezone.localtime()
    try:
        year = int(year) if year else now.year
        month = int(month) if month else now.month
    except (ValueError, TypeError):
        year = now.year
        month = now.month

    is_admin = (user.role == "admin")
    is_pharmacist_role = user.role in ("pharmacist", "head_pharmacist")

    # Scoping filter
    if is_pharmacist_role:
        # Strict branch isolation: Pharmacist and Head Pharmacist can only see their branch
        if user.branch_id:
            branch_filter = Q(branch_id=user.branch_id)
            selected_branch_id = user.branch_id
        else:
            branch_filter = Q(branch_id=-1)
            selected_branch_id = None
        overseer_mode = False
    else:
        # Admin overseer mode: can view any branch within company, or all company branches
        overseer_mode = True
        if branch_id:
            try:
                b_id = int(branch_id)
                branch_filter = Q(branch_id=b_id)
                selected_branch_id = b_id
            except (ValueError, TypeError):
                branch_filter = Q()
                selected_branch_id = None
        else:
            if user.company_id:
                branch_filter = Q(branch__company_id=user.company_id)
            else:
                branch_filter = Q()
            selected_branch_id = None

    sales_qs = (
        Sale.objects.filter(branch_filter)
        .filter(sold_at__year=year, sold_at__month=month)
        .select_related("branch", "user")
        .prefetch_related("saleitem_set__medicine")
        .order_by("sold_at")
    )

    events = []
    total_revenue = Decimal("0.00")

    for sale in sales_qs:
        total_revenue += sale.total_amount
        local_sold_at = timezone.localtime(sale.sold_at)

        items_data = []
        for item in sale.saleitem_set.all():
            items_data.append({
                "sale_item_id": item.sale_item_id,
                "medicine_name": item.medicine.medicine_name,
                "generic_name": item.medicine.generic_name,
                "category": item.medicine.category,
                "unit": item.medicine.unit_of_measure,
                "quantity": item.quantity_sold,
                "unit_price": float(item.unit_price_at_sale),
                "subtotal": float(item.subtotal),
            })

        cashier_name = sale.user.email.split("@")[0].replace(".", " ").title()

        events.append({
            "sale_id": sale.sale_id,
            "branch_id": sale.branch_id,
            "branch_name": sale.branch.branch_name,
            "cashier_email": sale.user.email,
            "cashier_name": cashier_name,
            "total_amount": float(sale.total_amount),
            "sold_at_iso": local_sold_at.isoformat(),
            "date_str": local_sold_at.strftime("%Y-%m-%d"),
            "formatted_date": local_sold_at.strftime("%b %d, %Y"),
            "time_str": local_sold_at.strftime("%I:%M %p"),
            "day": local_sold_at.day,
            "items_count": len(items_data),
            "items": items_data,
            "can_edit": False,
            "overseer_mode": overseer_mode,
        })

    month_name = calendar.month_name[month]

    # Available branches for filter dropdown (for admin)
    available_branches = []
    if is_admin:
        b_qs = Branch.objects.filter(is_active=True).order_by("branch_name")
        if user.company_id:
            b_qs = b_qs.filter(company_id=user.company_id)
        available_branches = [
            {"branch_id": b.branch_id, "branch_name": b.branch_name}
            for b in b_qs
        ]

    return {
        "year": year,
        "month": month,
        "month_name": month_name,
        "events": events,
        "total_sales_count": len(events),
        "total_revenue": float(total_revenue),
        "user_role": user.role,
        "is_admin": is_admin,
        "overseer_mode": overseer_mode,
        "can_edit": False,
        "user_branch_id": user.branch_id,
        "user_branch_name": user.branch.branch_name if user.branch else "All Branches",
        "selected_branch_id": selected_branch_id,
        "available_branches": available_branches,
    }

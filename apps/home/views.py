import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from apps.profiles.views import get_profile
from apps.register.models import Branch

from .models import Inventory, Medicine, Notification, Sale
from .utils import ensure_seed_sales, get_calendar_events_data


@method_decorator(login_required, name="dispatch")
class HomeScreen(View):
    def get(self, request):
        user = request.user
        profile = get_profile(user)

        branches = Branch.objects.filter(is_active=True).order_by("branch_name")
        medicines = Medicine.objects.filter(is_active=True)
        if user.company_id:
            branches = branches.filter(company_id=user.company_id)
            medicines = medicines.filter(company_id=user.company_id)

        # Scoping rule: Pharmacists and Head Pharmacists are strictly bound to their assigned branch
        scope = branches
        if user.role in ("pharmacist", "head_pharmacist") and user.branch_id:
            scope = branches.filter(branch_id=user.branch_id)

        scope_count = scope.count()
        if scope_count == 1:
            scope_label = scope.first().branch_name
        elif scope_count:
            scope_label = f"All branches ({scope_count})"
        else:
            scope_label = "No branches"

        # Ensure seed sales exist for seamless calendar demonstration
        ensure_seed_sales(company=user.company, branch=user.branch)

        # Calendar data preparation for Notion calendar
        calendar_data = get_calendar_events_data(user)
        calendar_json = json.dumps(calendar_data, cls=DjangoJSONEncoder)

        inventory = Inventory.objects.filter(branch__in=scope, medicine__is_active=True)
        out_filter = Q(quantity_on_hand__lte=0)
        low_filter = Q(quantity_on_hand__gt=0, quantity_on_hand__lte=F("reorder_threshold"))
        alerts = (
            inventory.filter(out_filter | low_filter)
            .select_related("medicine", "branch")
            .order_by("quantity_on_hand", "medicine__medicine_name")[:8]
        )

        sales = Sale.objects.filter(branch__in=scope)
        sales_today = sales.filter(sold_at__date=timezone.localdate())
        revenue_today = sales_today.aggregate(total=Sum("total_amount"))["total"] or 0

        notes = Notification.objects.filter(recipient_user=user)

        return render(request, "home/home.html", {
            "display_name": profile.first_name or user.email.split("@")[0],
            "role_label": user.get_role_display(),
            "is_admin": user.role == "admin",
            "is_head_pharmacist": user.role == "head_pharmacist",
            "is_pharmacist": user.role == "pharmacist",
            "phone": getattr(profile, profile.phone_field, ""),
            "license_number": getattr(profile, "license_number", ""),
            "scope_label": scope_label,
            "scope_count": scope_count,
            "branches": branches,
            "medicines_count": medicines.count(),
            "inventory_total": inventory.count(),
            "in_stock_count": inventory.filter(quantity_on_hand__gt=0).count(),
            "low_count": inventory.filter(low_filter).count(),
            "out_count": inventory.filter(out_filter).count(),
            "alerts": alerts,
            "sales_count": sales_today.count(),
            "revenue_today": revenue_today,
            "recent_sales": sales.select_related("branch", "user").order_by("-sold_at")[:5],
            "unread_count": notes.filter(is_read=False).count(),
            "notifications": notes.select_related("medicine", "branch").order_by("-created_at")[:5],
            # Calendar context
            "calendar_data": calendar_data,
            "calendar_json": calendar_json,
        })

    def post(self, request):
        if request.POST.get("action") == "mark_read":
            Notification.objects.filter(recipient_user=request.user, is_read=False).update(is_read=True)
            messages.success(request, "All notifications marked as read.")
        return redirect("home:home")


@login_required
def calendar_events(request):
    """
    JSON API endpoint for the Notion calendar view.
    Enforces strict branch scoping for Pharmacist and Head Pharmacist roles.
    Allows read-only company-wide oversight for Administrators.
    """
    year = request.GET.get("year")
    month = request.GET.get("month")
    branch_id = request.GET.get("branch")

    calendar_data = get_calendar_events_data(
        request.user,
        year=year,
        month=month,
        branch_id=branch_id,
    )
    return JsonResponse(calendar_data)


@login_required
def transaction_detail(request, sale_id):
    """
    JSON API endpoint to fetch detailed receipt information for a transaction.
    Pharmacists and Head Pharmacists can only inspect transactions from their assigned branch.
    Administrators can oversee any transaction in read-only mode without editing privileges.
    """
    user = request.user
    sale = get_object_or_404(
        Sale.objects.select_related("branch", "user").prefetch_related("saleitem_set__medicine"),
        pk=sale_id,
    )

    # Strict branch check for pharmacists and head pharmacists
    if user.role in ("pharmacist", "head_pharmacist"):
        if sale.branch_id != user.branch_id:
            return JsonResponse(
                {"error": "Unauthorized: You can only view transactions for your assigned branch."},
                status=403,
            )

    local_sold_at = timezone.localtime(sale.sold_at)
    items = []
    for item in sale.saleitem_set.all():
        items.append({
            "sale_item_id": item.sale_item_id,
            "medicine_name": item.medicine.medicine_name,
            "generic_name": item.medicine.generic_name,
            "category": item.medicine.category,
            "unit": item.medicine.unit_of_measure,
            "requires_prescription": item.medicine.requires_prescription,
            "quantity": item.quantity_sold,
            "unit_price": float(item.unit_price_at_sale),
            "subtotal": float(item.subtotal),
        })

    cashier_display = sale.user.email.split("@")[0].replace(".", " ").title()

    data = {
        "sale_id": sale.sale_id,
        "branch_id": sale.branch_id,
        "branch_name": sale.branch.branch_name,
        "branch_address": f"{sale.branch.street_address}, {sale.branch.city}",
        "branch_phone": sale.branch.branch_phone,
        "cashier_email": sale.user.email,
        "cashier_name": cashier_display,
        "total_amount": float(sale.total_amount),
        "sold_at": local_sold_at.strftime("%B %d, %Y at %I:%M %p"),
        "sold_at_date": local_sold_at.strftime("%b %d, %Y"),
        "sold_at_time": local_sold_at.strftime("%I:%M %p"),
        "is_admin_view": user.role == "admin",
        "can_edit": False,
        "overseer_notice": (
            "Admin Overseer Mode: Transaction records are read-only and immutable for compliance audit trails."
            if user.role == "admin"
            else "Branch Dispensing Record: Strictly recorded for your branch."
        ),
        "items": items,
        "items_count": len(items),
    }

    return JsonResponse(data)

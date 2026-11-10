from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from apps.profiles.views import get_profile
from apps.register.models import Branch

from .models import Inventory, Medicine, Notification, Sale


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

        scope = branches
        if user.role == "pharmacist" and user.branch_id:
            scope = branches.filter(branch_id=user.branch_id)
        scope_count = scope.count()
        if scope_count == 1:
            scope_label = scope.first().branch_name
        elif scope_count:
            scope_label = f"All branches ({scope_count})"
        else:
            scope_label = "No branches"

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
            "phone": getattr(profile, profile.phone_field),
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
        })

    def post(self, request):
        if request.POST.get("action") == "mark_read":
            Notification.objects.filter(recipient_user=request.user, is_read=False).update(is_read=True)
            messages.success(request, "All notifications marked as read.")
        return redirect("home:home")


# # from django.shortcuts import render

# # # Create your views here.

# # added - 09292026
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render
# from django.utils.decorators import method_decorator
# from django.views import View


# @method_decorator(login_required, name="dispatch")
# class HomeScreen(View):
#     def get(self, request):
#         return render(request, "home/home.html")

# # added - 09152026
# # from django.contrib.auth.decorators import login_required
# # from django.shortcuts import render
# # from django.utils.decorators import method_decorator
# # from django.views import View


# # @method_decorator(login_required, name="dispatch")
# # class HomeScreen(View):
# #     def get(self, request):
# #         return render(request, "home/home.html")
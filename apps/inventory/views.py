from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from apps.home.models import Inventory
from apps.notifications.rules import send_stock_request, stock_status

from .access import can_manage_catalogue, visible_branches, visible_medicines
from .forms import AddStockForm, AdjustStockForm, MedicineForm

OUT_Q = Q(quantity_on_hand__lte=0)
LOW_Q = Q(quantity_on_hand__gt=0, quantity_on_hand__lte=F("reorder_threshold"))
OK_Q = Q(quantity_on_hand__gt=0) & Q(quantity_on_hand__gt=F("reorder_threshold"))
STATUS_FILTERS = {"out": OUT_Q, "low": LOW_Q, "ok": OK_Q}


def first_error(form):
    field, errors = next(iter(form.errors.items()))
    prefix = "" if field == "__all__" else field.replace("_", " ").capitalize() + ": "
    return prefix + errors[0]


def attach_status(rows):
    needy = []
    for row in rows:
        row.status = stock_status(row.quantity_on_hand, row.reorder_threshold)
        row.elsewhere = []
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
        row.elsewhere = [
            item for item in by_medicine.get(row.medicine_id, [])
            if item.branch_id != row.branch_id and item.branch.company_id == row.branch.company_id
        ]


@method_decorator(login_required, name="dispatch")
class InventoryScreen(View):
    def get(self, request):
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
        if branch_id.isdigit() and int(branch_id) in {b.branch_id for b in branches}:
            rows = rows.filter(branch_id=int(branch_id))
        else:
            branch_id = ""
        status = request.GET.get("status", "")
        if status in STATUS_FILTERS:
            rows = rows.filter(STATUS_FILTERS[status])
        else:
            status = ""

        page = Paginator(rows.order_by("medicine__medicine_name", "branch__branch_name"), 15).get_page(request.GET.get("page"))
        page_rows = list(page.object_list)
        attach_status(page_rows)

        params = request.GET.copy()
        params.pop("page", None)

        return render(request, "inventory/inventory.html", {
            "page": page,
            "rows": page_rows,
            "counts": counts,
            "branches": branches,
            "medicines": visible_medicines(user).order_by("medicine_name"),
            "scope_count": len(branches),
            "scope_label": branches[0].branch_name if len(branches) == 1 else f"All branches ({len(branches)})",
            "can_manage_catalogue": can_manage_catalogue(user),
            "is_admin": user.role == "admin",
            "q": q,
            "branch_id": branch_id,
            "status": status,
            "querystring": params.urlencode(),
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
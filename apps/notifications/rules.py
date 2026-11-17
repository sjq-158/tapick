from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.mail import send_mass_mail
from django.db.models import Q
from django.utils import timezone

from apps.home.models import Inventory, Notification
from apps.user_settings.models import UserSettings

OUT, LOW, OK = "out", "low", "ok"
EMAIL_EVENTS = {"out_of_stock", "low_stock"}
REQUEST_COOLDOWN = timedelta(minutes=10)

TYPE_LABELS = {
    "out_of_stock": "Out of stock",
    "low_stock": "Low stock",
    "restocked": "Back in stock",
    "stock_request": "Stock request",
}


def stock_status(quantity, threshold):
    if quantity <= 0:
        return OUT
    if quantity <= threshold:
        return LOW
    return OK


def event_for(previous, current):
    if current == OUT and previous != OUT:
        return "out_of_stock"
    if current == LOW and previous in (None, OK):
        return "low_stock"
    if current == OK and previous in (OUT, LOW):
        return "restocked"
    return None


def stock_recipients(branch):
    User = get_user_model()
    return User.objects.filter(is_active=True).filter(
        Q(branch_id=branch.branch_id) | Q(role="head_pharmacist", company_id=branch.company_id)
    ).distinct()


def stocked_elsewhere(inventory):
    return (
        Inventory.objects.filter(
            medicine_id=inventory.medicine_id,
            branch__company_id=inventory.branch.company_id,
            branch__is_active=True,
            quantity_on_hand__gt=0,
        )
        .exclude(branch_id=inventory.branch_id)
        .select_related("branch")
        .order_by("-quantity_on_hand")
    )


def compose(event, inventory):
    medicine, branch = inventory.medicine, inventory.branch
    unit = medicine.unit_of_measure
    if event == "out_of_stock":
        message = f"{medicine} is out of stock at {branch}."
        others = list(stocked_elsewhere(inventory)[:3])
        if others:
            message += " In stock at: " + ", ".join(f"{o.branch} ({o.quantity_on_hand})" for o in others) + "."
        return "Out of stock", message
    if event == "low_stock":
        return "Low stock", (
            f"{medicine} is running low at {branch}: {inventory.quantity_on_hand} {unit} left "
            f"(reorder at {inventory.reorder_threshold})."
        )
    return "Back in stock", f"{medicine} is above its reorder level at {branch}: {inventory.quantity_on_hand} {unit} on hand."


def notify(recipients, branch, medicine, notification_type, title, message):
    rows = [
        Notification(
            branch=branch,
            medicine=medicine,
            recipient_user=user,
            notification_type=notification_type,
            title=title[:255],
            message=message[:255],
        )
        for user in recipients
    ]
    return Notification.objects.bulk_create(rows)


def email_alerts(recipients, subject, message):
    muted = set(
        UserSettings.objects.filter(user__in=recipients, email_notifications=False).values_list("user_id", flat=True)
    )
    mails = [
        (f"[Tapick] {subject}", message, None, [user.email])
        for user in recipients
        if user.email and user.pk not in muted
    ]
    if mails:
        send_mass_mail(mails, fail_silently=True)


def handle_stock_change(inventory, previous):
    current = stock_status(inventory.quantity_on_hand, inventory.reorder_threshold)
    event = event_for(previous, current)
    if not event:
        return
    title, message = compose(event, inventory)
    recipients = list(stock_recipients(inventory.branch))
    notify(recipients, inventory.branch, inventory.medicine, event, title, message)
    if event in EMAIL_EVENTS:
        email_alerts(recipients, title, message)


def send_stock_request(inventory, requester):
    on_hand = {item.branch_id: item.quantity_on_hand for item in stocked_elsewhere(inventory)}
    if not on_hand:
        return "none", 0

    staff = get_user_model().objects.filter(is_active=True, branch_id__in=on_hand).exclude(pk=requester.pk)
    recent = set(
        Notification.objects.filter(
            notification_type="stock_request",
            branch_id=inventory.branch_id,
            medicine_id=inventory.medicine_id,
            created_at__gte=timezone.now() - REQUEST_COOLDOWN,
        ).values_list("recipient_user_id", flat=True)
    )
    staff = [user for user in staff if user.pk not in recent]
    if not staff:
        return "skipped", 0

    medicine, branch = inventory.medicine, inventory.branch
    Notification.objects.bulk_create([
        Notification(
            branch=branch,
            medicine=medicine,
            recipient_user=user,
            notification_type="stock_request",
            title=f"Stock request from {branch}"[:255],
            message=(
                f"{branch} needs {medicine}. You have {on_hand[user.branch_id]} {medicine.unit_of_measure} "
                f"on hand. Requested by {requester.email}."
            )[:255],
        )
        for user in staff
    ])
    return "sent", len(staff)
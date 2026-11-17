from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateformat import format as date_format
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.http import require_POST

from apps.home.models import Notification

from .rules import TYPE_LABELS


def mine(request):
    return Notification.objects.filter(recipient_user=request.user)


def go_back(request):
    target = request.POST.get("next", "")
    allowed = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return redirect(target if allowed else "notifications:list")


@method_decorator(login_required, name="dispatch")
class NotificationScreen(View):
    def get(self, request):
        kind = request.GET.get("type", "")
        only_unread = request.GET.get("unread") == "1"

        rows = mine(request).select_related("medicine", "branch").order_by("-created_at", "-notification_id")
        if kind in TYPE_LABELS:
            rows = rows.filter(notification_type=kind)
        else:
            kind = ""
        if only_unread:
            rows = rows.filter(is_read=False)

        page = Paginator(rows, 15).get_page(request.GET.get("page"))
        params = request.GET.copy()
        params.pop("page", None)

        return render(request, "notifications/notifications.html", {
            "page": page,
            "kind": kind,
            "only_unread": only_unread,
            "type_options": TYPE_LABELS.items(),
            "unread_count": mine(request).filter(is_read=False).count(),
            "total_count": mine(request).count(),
            "querystring": params.urlencode(),
        })


@login_required
@require_POST
def mark_read(request, pk):
    mine(request).filter(pk=pk).update(is_read=True)
    return go_back(request)


@login_required
@require_POST
def mark_all_read(request):
    mine(request).filter(is_read=False).update(is_read=True)
    return go_back(request)


@login_required
@require_POST
def delete(request, pk):
    mine(request).filter(pk=pk).delete()
    return go_back(request)


def serialize(note):
    return {
        "id": note.notification_id,
        "title": note.title,
        "message": note.message,
        "type": note.notification_type,
        "type_label": TYPE_LABELS.get(note.notification_type, note.notification_type),
        "medicine": str(note.medicine),
        "branch": str(note.branch),
        "is_read": note.is_read,
        "created": date_format(timezone.localtime(note.created_at), "M j, g:i A"),
    }


@login_required
def recent(request):
    """Return the 5 most-recent notifications for the header dropdown panel."""
    rows = mine(request).select_related("medicine", "branch").order_by("-created_at", "-notification_id")[:5]
    return JsonResponse({
        "unread": mine(request).filter(is_read=False).count(),
        "items": [serialize(note) for note in rows],
    })


@login_required
def poll(request):
    rows = mine(request)
    latest = rows.order_by("-notification_id").values_list("notification_id", flat=True).first() or 0
    items = []
    after = request.GET.get("after", "")
    if after.isdigit():
        fresh = rows.filter(notification_id__gt=int(after)).select_related("medicine", "branch")
        items = [serialize(note) for note in fresh.order_by("notification_id")[:20]]
    return JsonResponse({
        "unread": rows.filter(is_read=False).count(),
        "latest_id": latest,
        "items": items,
    })

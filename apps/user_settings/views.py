from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from .models import UserSettings


@method_decorator(login_required, name="dispatch")
class SettingsScreen(View):
    def get(self, request):
        prefs, _ = UserSettings.objects.get_or_create(user=request.user)
        return render(request, "user_settings/settings.html", {
            "settings_obj": prefs,
        })

    def post(self, request):
        prefs, _ = UserSettings.objects.get_or_create(user=request.user)
        prefs.dark_mode = "dark_mode" in request.POST
        prefs.email_notifications = "email_notifications" in request.POST
        prefs.save()
        messages.success(request, "Preferences saved successfully.")
        return redirect("user_settings:settings")


@login_required
@require_POST
def set_theme(request):
    prefs, _ = UserSettings.objects.get_or_create(user=request.user)
    prefs.dark_mode = request.POST.get("theme") == "dark"
    prefs.save(update_fields=["dark_mode"])
    return JsonResponse({"theme": "dark" if prefs.dark_mode else "light"})

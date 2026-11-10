from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from .models import UserSettings


@method_decorator(login_required, name="dispatch")
class SettingsScreen(View):
    def page(self, request, prefs, password_form):
        return render(request, "user_settings/settings.html", {
            "settings_obj": prefs,
            "password_form": password_form,
        })

    def get(self, request):
        prefs, _ = UserSettings.objects.get_or_create(user=request.user)
        return self.page(request, prefs, PasswordChangeForm(request.user))

    def post(self, request):
        prefs, _ = UserSettings.objects.get_or_create(user=request.user)

        if request.POST.get("action") == "password":
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated.")
                return redirect("user_settings:settings")
            return self.page(request, prefs, form)

        prefs.dark_mode = "dark_mode" in request.POST
        prefs.email_notifications = "email_notifications" in request.POST
        prefs.save()
        messages.success(request, "Settings saved.")
        return redirect("user_settings:settings")


@login_required
@require_POST
def set_theme(request):
    prefs, _ = UserSettings.objects.get_or_create(user=request.user)
    prefs.dark_mode = request.POST.get("theme") == "dark"
    prefs.save(update_fields=["dark_mode"])
    return JsonResponse({"theme": "dark" if prefs.dark_mode else "light"})

# # from django.shortcuts import render

# # # Create your views here.

# # added
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect
# from django.utils.decorators import method_decorator
# from django.views import View

# from .models import UserSettings


# @method_decorator(login_required, name="dispatch")
# class SettingsScreen(View):
#     def get(self, request):
#         settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
#         return render(request, "user_settings/settings.html", {"settings_obj": settings_obj})

#     def post(self, request):
#         settings_obj, _ = UserSettings.objects.get_or_create(user=request.user)
#         settings_obj.dark_mode = "dark_mode" in request.POST
#         settings_obj.email_notifications = "email_notifications" in request.POST
#         settings_obj.save()
#         return redirect("user_settings:settings")
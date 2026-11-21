from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View


@method_decorator(login_required, name="dispatch")
class ChangePasswordScreen(View):
    def get(self, request):
        form = PasswordChangeForm(request.user)
        return render(request, "change_password/change_password.html", {
            "form": form,
        })

    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated.")
            return redirect("user_settings:settings")
        return render(request, "change_password/change_password.html", {
            "form": form,
        })

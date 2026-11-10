from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"placeholder": "you@pharmacy.com", "autofocus": True, "autocomplete": "email"}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "••••••••••••", "autocomplete": "current-password"}
        )


def safe_next(request):
    target = request.POST.get("next") or request.GET.get("next") or ""
    allowed = url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return target if allowed else ""


class LoginScreen(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home:home")
        return render(request, "login/login.html", {"form": LoginForm(), "next": safe_next(request)})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(safe_next(request) or "home:home")
        return render(request, "login/login.html", {"form": form, "next": safe_next(request)})


class LogoutScreen(View):
    def get(self, request):
        logout(request)
        messages.info(request, "You have been signed out.")
        return redirect("login:login")

# # from django.shortcuts import render

# # # Create your views here.

# # added - 09292026
# from django.contrib.auth import login, logout
# from django.contrib.auth.forms import AuthenticationForm
# from django.shortcuts import redirect, render
# from django.views import View


# class LoginForm(AuthenticationForm):
#     """AuthenticationForm with placeholders. The login field is the email (USERNAME_FIELD)."""

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.fields["username"].widget.attrs.update(
#             {"placeholder": "Enter your email", "autofocus": True}
#         )
#         self.fields["password"].widget.attrs.update({"placeholder": "••••••••••••"})


# class LoginScreen(View):
#     def get(self, request):
#         return render(request, "login/login.html", {"form": LoginForm()})

#     def post(self, request):
#         form = LoginForm(request, data=request.POST)
#         if form.is_valid():
#             login(request, form.get_user())
#             return redirect("home:home")
#         return render(request, "login/login.html", {"form": form})


# class LogoutScreen(View):
#     def get(self, request):
#         logout(request)
#         return redirect("login:login")

# # added - 09152026from django.contrib.auth.forms import AuthenticationForm
# # from django.contrib.auth import login, logout
# # from django.shortcuts import render, redirect
# # from django.views import View


# # class LoginScreen(View):
# #     def get(self, request):
# #         form = AuthenticationForm()
# #         return render(request, "login/login.html", {"form": form})

# #     def post(self, request):
# #         form = AuthenticationForm(request, data=request.POST)
# #         if form.is_valid():
# #             login(request, form.get_user())
# #             return redirect("home:home")
# #         return render(request, "login/login.html", {"form": form})


# # class LogoutScreen(View):
# #     def get(self, request):
# #         logout(request)
# #         return redirect("login:login")
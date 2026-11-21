from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from apps.login.views import LoginForm
from .forms import RegisterForm


class RegisterScreen(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("home:home")
        login_form = LoginForm()
        register_form = RegisterForm()
        return render(request, "register/register.html", {
            "form": register_form,
            "register_form": register_form,
            "login_form": login_form,
            "mode": "register",
        })

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. You can sign in now.")
            return redirect("login:login")
        return render(request, "register/register.html", {
            "form": form,
            "register_form": form,
            "login_form": LoginForm(),
            "mode": "register",
        })

# # from django.shortcuts import render

# # # Create your views here.

# # added - 09292026
# from django.shortcuts import render, redirect
# from django.views import View

# from .forms import RegisterForm


# class RegisterScreen(View):
#     def get(self, request):
#         form = RegisterForm()
#         return render(request, "register/register.html", {"form": form})

#     def post(self, request):
#         form = RegisterForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect("login:login")
#         return render(request, "register/register.html", {"form": form})


# # added - 09152026
# # from django.contrib.auth.forms import UserCreationForm
# # from django.shortcuts import render, redirect
# # from django.views import View


# # class RegisterScreen(View):
# #     def get(self, request):
# #         form = UserCreationForm()
# #         return render(request, "register/register.html", {"form": form})

# #     def post(self, request):
# #         form = UserCreationForm(request.POST)
# #         if form.is_valid():
# #             form.save()
# #             return redirect("login:login")
# #         return render(request, "register/register.html", {"form": form})
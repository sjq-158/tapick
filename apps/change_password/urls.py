from django.urls import path
from . import views

app_name = "change_password"

urlpatterns = [
    path("", views.ChangePasswordScreen.as_view(), name="change_password"),
]

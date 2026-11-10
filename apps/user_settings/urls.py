from django.urls import path

from .views import SettingsScreen, set_theme

app_name = "user_settings"

urlpatterns = [
    path("", SettingsScreen.as_view(), name="settings"),
    path("theme/", set_theme, name="theme"),
]

# # newly added
# from django.urls import path
# from .views import SettingsScreen

# app_name = "user_settings"

# urlpatterns = [
#     path("", SettingsScreen.as_view(), name="settings"),
# ]
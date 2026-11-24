from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.HomeScreen.as_view(), name="home"),
    path("calendar/events/", views.calendar_events, name="calendar_events"),
    path("calendar/transaction/<int:sale_id>/", views.transaction_detail, name="transaction_detail"),
]

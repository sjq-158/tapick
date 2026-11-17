from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.InventoryScreen.as_view(), name="list"),
    path("add/", views.add_stock, name="add"),
    path("medicine/add/", views.add_medicine, name="add_medicine"),
    path("<int:pk>/update/", views.update_stock, name="update"),
    path("<int:pk>/request/", views.request_stock, name="request_stock"),
]
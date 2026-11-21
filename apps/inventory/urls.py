from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.InventoryScreen.as_view(), name="list"),
    path("add/", views.add_stock, name="add"),
    path("medicine/add/", views.add_medicine, name="add_medicine"),
    path("<int:pk>/update/", views.update_stock, name="update"),
    path("<int:pk>/request/", views.request_stock, name="request_stock"),
    path("upload/", views.upload_file, name="upload"),
    path("template/", views.download_template, name="template"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path("live-status/", views.live_status, name="live_status"),
    path("locate/", views.locate_medicine, name="locate"),
    path("notify-branch/", views.send_branch_notice, name="notify_branch"),
]

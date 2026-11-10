from django.contrib import admin

from .models import Inventory, Medicine, Notification, Sale, SaleItem


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ("medicine_name", "generic_name", "category", "unit_price", "company", "is_active")
    list_filter = ("company", "category", "is_active", "requires_prescription")
    search_fields = ("medicine_name", "generic_name", "brand_name")


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("medicine", "branch", "quantity_on_hand", "reorder_threshold", "last_updated")
    list_filter = ("branch",)
    search_fields = ("medicine__medicine_name", "branch__branch_name")


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("sale_id", "branch", "user", "total_amount", "sold_at")
    list_filter = ("branch",)
    inlines = [SaleItemInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "branch", "medicine", "recipient_user", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "branch")


admin.site.register(SaleItem)

# # added - 09292026
# from django.contrib import admin

# from .models import Inventory, Medicine, Notification, Sale, SaleItem

# admin.site.register(Medicine)
# admin.site.register(Inventory)
# admin.site.register(Sale)
# admin.site.register(SaleItem)
# admin.site.register(Notification)

# # edited - 09292026
# # from django.contrib import admin

# # # Register your models here.

from django.contrib import admin

from .models import Branch, Company, User


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_email", "contact_phone", "is_active")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("branch_name", "company", "city", "branch_phone", "is_active")
    list_filter = ("company", "city", "is_active")
    search_fields = ("branch_name", "city", "street_address")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("user_id", "email", "role", "company", "branch", "is_active")
    list_filter = ("role", "company", "is_active")
    search_fields = ("email",)
    readonly_fields = ("password",)

    def has_add_permission(self, request):
        return False

# # added - 09292026
# from django.contrib import admin

# from .models import Branch, Company, User

# admin.site.register(Company)
# admin.site.register(Branch)


# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ("user_id", "email", "role", "company", "branch", "is_active")
#     readonly_fields = ("password",)

#     def has_add_permission(self, request):
#         return False  # accounts are created via /register/ or createsuperuser (hashed passwords)


# # edited - 09292026
# # from django.contrib import admin

# # # Register your models here.

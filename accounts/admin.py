from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from django.utils.translation import gettext_lazy as _
from .models import MyUser, OTP

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("__str__", "secret")
    search_fields = ("email", "phone")

@admin.register(MyUser)
class MyUserAdmin(UserAdmin, ExportActionModelAdmin, ImportExportModelAdmin):
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )
    list_display = ("username", "email", "phone", "first_name", "last_name", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email", "phone")




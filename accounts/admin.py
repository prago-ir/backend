from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ExportActionModelAdmin, ImportExportModelAdmin
from django.utils.translation import gettext_lazy as _
from .models import MyUser, OTP, Author, Teacher, Organizer, Profile

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("__str__", "secret")
    search_fields = ("email", "phone")


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(MyUser)
class MyUserAdmin(UserAdmin, ExportActionModelAdmin, ImportExportModelAdmin):
    model = MyUser
    list_display = ("username", "email", "phone", "first_name", "last_name", "is_staff", "get_roles_display")
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    inlines = [ProfileInline]
    
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "phone")}),
        (
            "Permissions",
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
        ("Important dates", {"fields": ("last_login", "date_joined")}),
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
    
    def get_roles_display(self, obj):
        return ", ".join(obj.get_roles())
    get_roles_display.short_description = 'نقش‌ها'
    


admin.site.register(Teacher)
admin.site.register(Organizer)
admin.site.register(Author)



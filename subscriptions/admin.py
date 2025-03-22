from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_days', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['included_courses']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active']

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'subscription_plan', 'start_date', 'end_date', 'is_active', 'is_valid']
    list_filter = ['is_active', 'start_date', 'end_date', 'subscription_plan']
    search_fields = ['user__username', 'user__email', 'subscription_plan__name']
    readonly_fields = ['start_date']
    raw_id_fields = ['user']
    list_editable = ['is_active']
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'اعتبار'

from django.contrib import admin
from .models import Coupon, Order, Transaction

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'is_active', 'valid_from', 'valid_to', 'usage_limit', 'times_used']
    list_filter = ['is_active', 'discount_type', 'valid_from', 'valid_to']
    search_fields = ['code', 'description']
    readonly_fields = ['times_used', 'created_at', 'updated_at']
    list_editable = ['is_active']
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'description', 'is_active')
        }),
        ('Discount Information', {
            'fields': ('discount_type', 'discount_value')
        }),
        ('Usage Information', {
            'fields': ('usage_limit', 'times_used')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'order_type', 'status', 'total_amount', 'discount_amount', 'final_amount', 'created_at', 'paid_at']
    list_filter = ['status', 'order_type', 'created_at', 'paid_at']
    search_fields = ['order_number', 'user__username', 'user__email']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'paid_at']
    raw_id_fields = ['user', 'course', 'subscription_plan', 'coupon']
    fieldsets = (
        ('Basic Information', {
            'fields': ('order_number', 'user', 'status', 'order_type')
        }),
        ('Purchase Items', {
            'fields': ('course', 'subscription_plan')
        }),
        ('Financial Information', {
            'fields': ('total_amount', 'discount_amount', 'final_amount', 'coupon')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of paid orders
        if obj and obj.status == 'paid':
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'order', 'amount', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'order__order_number', 'order__user__username', 'order__user__email']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['order']
    fieldsets = (
        ('Basic Information', {
            'fields': ('transaction_id', 'order', 'amount', 'status')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_gateway_reference')
        }),
        ('Additional Information', {
            'fields': ('description', 'extra_data')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

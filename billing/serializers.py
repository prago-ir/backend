from rest_framework import serializers
from .models import Order
# If you have OrderItem and want to show item details, you might import OrderItemSimpleSerializer too.


class UserOrderListSerializer(serializers.ModelSerializer):
    order_type_display = serializers.CharField(
        source='get_order_type_display', read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    # If you want to format dates/times specifically, you can use DateTimeField with format argument
    # created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)
    # paid_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True, allow_null=True)

    class Meta:
        model = Order
        fields = [
            'id',  # Good for keys and linking
            'order_number',
            'order_type_display',
            'status_display',
            # Raw status for frontend logic if needed (e.g., badge coloring)
            'status',
            'total_amount',
            'discount_amount',
            'final_amount',
            'created_at',
            'paid_at',
        ]

from rest_framework import serializers
from .models import SubscriptionPlan
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    # These CharField declarations will be populated by to_representation
    current_price = serializers.CharField(read_only=True)
    original_price = serializers.CharField(read_only=True)
    has_special_offer = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'slug', 'description',
            'original_price',   # String version, populated by to_representation
            'current_price',    # String version, populated by to_representation
            'has_special_offer',
            'duration_days',
            'is_active',
        ]

    # This method is now a helper for to_representation, not tied to a SerializerMethodField
    def _get_decimal_current_price(self, obj: SubscriptionPlan) -> Decimal:
        price_val = obj.get_current_price()  # Model's method
        if price_val is None:
            logger.warning(
                f"Model's get_current_price for plan {obj.id} ('{obj.name}') returned None. Defaulting to Decimal('0').")
            return Decimal('0')
        return price_val

    def get_has_special_offer(self, obj: SubscriptionPlan) -> bool:
        return obj.has_active_special_offer()

    def to_representation(self, instance: SubscriptionPlan) -> dict:
        """
        Convert `instance` into the representation that is used for rendering.
        """
        representation = super().to_representation(instance)

        # --- Current Price (String) ---
        current_price_decimal = self._get_decimal_current_price(instance)
        representation['current_price'] = "{:.0f}".format(
            current_price_decimal)

        # --- Original Price (String) ---
        original_price_decimal = instance.price  # Direct from model
        if original_price_decimal is None:  # Should not happen if model field is not nullable
            logger.error(
                f"to_representation: original_price_decimal (instance.price) is None for plan {instance.id}. Defaulting to '0'.")
            representation['original_price'] = "0"
        else:
            representation['original_price'] = "{:.0f}".format(
                original_price_decimal)

        return representation

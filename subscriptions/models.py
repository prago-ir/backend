from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone  # Ensure timezone is imported
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام اشتراک')
    slug = models.SlugField(max_length=100, unique=True,
                            verbose_name='اسلاگ اشتراک')
    description = models.TextField(verbose_name='توضیحات اشتراک')
    price = models.DecimalField(
        max_digits=9, decimal_places=0, verbose_name='قیمت اصلی')  # This should not be None
    duration_days = models.PositiveIntegerField(verbose_name='مدت زمان (روز)')
    included_courses = models.ManyToManyField(
        'courses.Course',
        blank=True,
        related_name='subscription_plans',
        verbose_name='دوره‌های شامل شده'
    )
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='تاریخ بروزرسانی')

    # Special offer fields
    special_offer_price = models.DecimalField(
        max_digits=9, decimal_places=0, null=True, blank=True, verbose_name='قیمت ویژه'
    )
    special_offer_start_date = models.DateTimeField(
        null=True, blank=True, verbose_name='تاریخ شروع پیشنهاد ویژه'
    )
    special_offer_end_date = models.DateTimeField(  # Make sure this field is present in your model
        null=True, blank=True, verbose_name='تاریخ پایان پیشنهاد ویژه'
    )

    class Meta:
        verbose_name = 'اشتراک'
        verbose_name_plural = 'اشتراک‌ها'

    def __str__(self):
        return self.name

    def has_active_special_offer(self) -> bool:
        now = timezone.now()
        
        # Check if essential special offer details are present
        if self.special_offer_price is None or not self.special_offer_start_date:
            return False

        # Check if the offer has started
        if self.special_offer_start_date > now:
            return False

        # Check if the offer has an end date and if it has passed
        if self.special_offer_end_date is not None and self.special_offer_end_date < now:
            return False
            
        # If all checks pass (or end date is None and offer has started), the offer is active
        return True

    def get_current_price(self) -> Decimal:
        """
        Get the current price considering any active special offers.
        This method MUST always return a Decimal.
        """
        if self.has_active_special_offer() and self.special_offer_price is not None:
            return self.special_offer_price

        if self.price is None:
            # This should not happen if 'price' is non-nullable and always set.
            logger.error(
                f"SubscriptionPlan ID {self.id} ('{self.name}') has a None value for 'price'. Defaulting to Decimal('0.00').")
            return Decimal('0.00')
        return self.price


class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='subscriptions', verbose_name='کاربر')
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='user_subscriptions',
                                          verbose_name='اشتراک')
    start_date = models.DateTimeField(
        auto_now_add=True, verbose_name='تاریخ شروع')
    end_date = models.DateTimeField(verbose_name='تاریخ پایان')
    is_active = models.BooleanField(default=True, verbose_name='فعال')

    class Meta:
        verbose_name = 'اشتراک کاربر'
        verbose_name_plural = 'اشتراک‌های کاربر'

    def __str__(self):
        return f"{self.user.username} - {self.subscription_plan.name}"

    def is_valid(self):
        """Check if the subscription is still valid"""
        from django.utils import timezone
        return self.is_active and self.end_date > timezone.now()

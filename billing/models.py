from django.db import models
from django.utils import timezone

# Create your models here.

class Coupon(models.Model):
    """
    Model representing discount coupons that can be used during checkout.
    Supports both percentage and fixed amount discounts.
    """
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage discount'),
        ('fixed', 'Fixed amount discount'),
    ]
    
    # Basic information
    code = models.CharField(max_length=50, unique=True, help_text="Coupon code that users will enter")
    description = models.TextField(blank=True, help_text="Description of the coupon")
    
    # Discount information
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Percentage or fixed amount")
    
    # Usage information
    usage_limit = models.PositiveIntegerField(default=0, help_text="Maximum number of times this coupon can be used (0 for unlimited)")
    times_used = models.PositiveIntegerField(default=0, help_text="Number of times this coupon has been used")
    
    # Scheduling information
    valid_from = models.DateTimeField(default=timezone.now, help_text="When this coupon becomes valid")
    valid_to = models.DateTimeField(null=True, blank=True, help_text="When this coupon expires (null for never)")
    
    # Active flag
    is_active = models.BooleanField(default=True, help_text="Whether this coupon is currently active")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'کد تخفیف'
        verbose_name_plural = 'کدهای تخفیف'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.code
    
    @property
    def is_valid(self):
        """Check if the coupon is currently valid based on dates and usage"""
        now = timezone.now()
        
        # Check if coupon is active
        if not self.is_active:
            return False
        
        # Check if coupon has expired
        if self.valid_to and now > self.valid_to:
            return False
            
        # Check if coupon is not yet valid
        if now < self.valid_from:
            return False
            
        # Check if usage limit has been reached
        if self.usage_limit > 0 and self.times_used >= self.usage_limit:
            return False
            
        return True
    
    def apply_discount(self, amount):
        """
        Apply the coupon discount to the given amount
        
        Args:
            amount: The original amount to discount
            
        Returns:
            The discounted amount
        """
        if not self.is_valid:
            return amount
            
        if self.discount_type == 'percentage':
            discount_amount = amount * (self.discount_value / 100)
        else:  # fixed amount
            discount_amount = min(amount, self.discount_value)  # Don't discount more than the amount
            
        return max(amount - discount_amount, 0)  # Don't go below zero
    
    def record_usage(self):
        """Record that this coupon has been used once"""
        self.times_used += 1
        self.save(update_fields=['times_used'])


# Add after the existing Coupon model

class Order(models.Model):
    """
    Model representing a user's order for courses or subscriptions
    """
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
    ]
    
    ORDER_TYPE_CHOICES = [
        ('course', 'Course Purchase'),
        ('subscription', 'Subscription Purchase'),
    ]
    
    # Basic information
    user = models.ForeignKey('accounts.MyUser', on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    
    # Items being purchased (one of these will be null depending on order_type)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    subscription_plan = models.ForeignKey('subscriptions.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Financial information
    total_amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='مبلغ کل')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='مبلغ تخفیف')
    final_amount = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='مبلغ نهایی')
    
    # Coupon information (if used)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پرداخت')
    
    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارش‌ها'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        # Generate order number if not provided
        if not self.order_number:
            import uuid
            self.order_number = str(uuid.uuid4()).split('-')[0].upper()
            
        # Calculate final amount
        if not self.final_amount:
            self.final_amount = self.total_amount - self.discount_amount
            
        super().save(*args, **kwargs)
    
    def mark_as_paid(self):
        """Mark the order as paid and process the purchase"""
        from django.utils import timezone
        
        if self.status != 'paid':
            self.status = 'paid'
            self.paid_at = timezone.now()
            self.save(update_fields=['status', 'paid_at'])
            
            # Process the purchase based on order type
            if self.order_type == 'course' and self.course:
                from enrollments.models import Enrollment
                Enrollment.objects.get_or_create(
                    user=self.user,
                    course=self.course,
                    defaults={'is_active': True}
                )
            elif self.order_type == 'subscription' and self.subscription_plan:
                from subscriptions.models import UserSubscription
                from django.utils import timezone
                
                # Calculate end date based on subscription plan duration
                end_date = timezone.now() + timezone.timedelta(days=self.subscription_plan.duration_days)
                
                UserSubscription.objects.create(
                    user=self.user,
                    subscription_plan=self.subscription_plan,
                    end_date=end_date,
                    is_active=True
                )


# Add after the Order model

class Transaction(models.Model):
    """
    Model representing payment transactions for orders
    """
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('zarinpal', 'Zarinpal'),
        # ('idpay', 'IDPay'),
        # ('payping', 'PayPing'),
        # ('other', 'Other'),
    ]
    
    # Basic information
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=0)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_gateway_reference = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional information
    description = models.TextField(blank=True)
    extra_data = models.JSONField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'تراکنش'
        verbose_name_plural = 'تراکنش‌ها'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Transaction {self.transaction_id} for Order #{self.order.order_number}"
    
    def mark_as_successful(self):
        """Mark transaction as successful and update the related order"""
        if self.status != 'successful':
            self.status = 'successful'
            self.save(update_fields=['status'])
            
            # Mark the order as paid
            self.order.mark_as_paid()
    
    def mark_as_failed(self, reason=None):
        """Mark transaction as failed with optional reason"""
        if self.status != 'failed':
            self.status = 'failed'
            if reason:
                self.description = f"{self.description}\nFailure reason: {reason}".strip()
            self.save(update_fields=['status', 'description'])

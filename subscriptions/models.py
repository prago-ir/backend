from django.db import models
from django.contrib.auth import get_user_model

from courses.models import Course


User = get_user_model()


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام اشتراک')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='اسلاگ اشتراک')
    description = models.TextField(verbose_name='توضیحات اشتراک')
    price = models.DecimalField(max_digits=9, decimal_places=0, verbose_name='قیمت')
    duration_days = models.PositiveIntegerField(verbose_name='مدت زمان (روز)')
    included_courses = models.ManyToManyField(Course, blank=True, related_name='subscription_plans', 
                                           verbose_name='دوره‌های شامل شده')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    class Meta:
        verbose_name = 'اشتراک'
        verbose_name_plural = 'اشتراک‌ها'

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='کاربر')
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='user_subscriptions',
                                         verbose_name='اشتراک')
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ شروع')
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
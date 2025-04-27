from django.db import models
from django.utils import timezone

from subscriptions.models import UserSubscription
from taxonomy.models import Category, Tag
from accounts.models import Organizer, Teacher


class Attribute(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام ویژگی')
    value = models.CharField(max_length=255, verbose_name='مقدار ویژگی')

    def __str__(self):
        return f"{self.name}: {self.value}"

    class Meta:
        verbose_name = 'ویژگی'
        verbose_name_plural = 'ویژگی‌ها'


class Course(models.Model):
    PUBLISHED_STATUS = (
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
    )
    
    cover_image = models.ImageField(verbose_name='تصویر دوره', upload_to='cover_image')
    title = models.CharField(max_length=100, verbose_name='تیتر دوره')
    latin_title = models.CharField(max_length=100, verbose_name='تیتر لاتین دوره')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='اسلاگ دوره')
    description = models.TextField(verbose_name='توضیحات کامل دوره')
    price = models.DecimalField(max_digits=9, decimal_places=0, verbose_name='قیمت')
    
    # Published status
    status = models.CharField(max_length=20, choices=PUBLISHED_STATUS, default='draft', 
                             verbose_name='وضعیت انتشار')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انتشار')
    
    # Special offer fields
    special_offer_price = models.DecimalField(max_digits=9, decimal_places=0, null=True, blank=True, 
                                            verbose_name='قیمت ویژه')
    special_offer_start_date = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ شروع پیشنهاد ویژه')
    special_offer_end_date = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پایان پیشنهاد ویژه')
    
    intro_video_link = models.URLField(verbose_name='لینک ویدیو معرفی')
    total_hours = models.DecimalField(max_digits=5, decimal_places=1, verbose_name='مجموع ساعات')

    # Relationships
    organizers = models.ManyToManyField(Organizer, related_name='organized_courses', verbose_name='برگزار کننده‌ها')
    teachers = models.ManyToManyField(Teacher, related_name='teaching_courses', verbose_name='مدرس‌ها')
    attributes = models.ManyToManyField(Attribute, related_name='courses', verbose_name='ویژگی‌ها')
    tags = models.ManyToManyField(Tag, related_name='courses', verbose_name='تگ‌ها')
    categories = models.ManyToManyField(Category, related_name='courses', verbose_name='دسته‌بندی‌ها')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'دوره'
        verbose_name_plural = 'دوره‌ها'
    
    def save(self, *args, **kwargs):
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
        
    def is_free_for_user(self, user):
        """Check if the course is free for a specific user via their subscriptions"""
        from django.utils import timezone
        return UserSubscription.objects.filter(
            user=user,
            is_active=True,
            end_date__gt=timezone.now(),
            subscription_plan__included_courses=self
        ).exists()
        
    def has_active_special_offer(self):
        """Check if the course currently has an active special offer"""
        now = timezone.now()
        return (
            self.special_offer_price is not None and
            self.special_offer_start_date is not None and
            self.special_offer_end_date is not None and
            self.special_offer_start_date <= now <= self.special_offer_end_date
        )
    
    def get_current_price(self):
        """Get the current price considering any active special offers"""
        if self.has_active_special_offer():
            return self.special_offer_price
        return self.price


class Chapter(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='chapters', verbose_name='دوره')
    number = models.PositiveSmallIntegerField(verbose_name='شماره فصل')
    title = models.CharField(max_length=100, verbose_name='عنوان فصل')
    description = models.TextField(blank=True, verbose_name='توضیحات فصل')

    def __str__(self):
        return f"فصل {self.number}: {self.title}"

    class Meta:
        verbose_name = 'فصل'
        verbose_name_plural = 'فصل‌ها'

class Episode(models.Model):
    EPISODE_TYPES = (
        ('video', 'ویدیو'),
        ('file', 'فایل'),
        ('text', 'متن'),
        ('quiz', 'آزمون'),
    )
    
    PUBLISHED_STATUS = (
        ('draft', 'پیش‌نویس'),
        ('published', 'منتشر شده'),
        ('archived', 'بایگانی شده'),
    )

    title = models.CharField(max_length=200, verbose_name='عنوان اپیزود')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='episodes', verbose_name='فصل')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='episodes', verbose_name='دوره')
    type = models.CharField(max_length=10, choices=EPISODE_TYPES, default='video', verbose_name='نوع')
    thumbnail = models.ImageField(upload_to='episode_thumbnails', blank=True, null=True,
                                  verbose_name='تصویر بند انگشتی')
    content_url = models.URLField(verbose_name='آدرس محتوا')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    
    # Published status
    status = models.CharField(max_length=20, choices=PUBLISHED_STATUS, default='draft', 
                             verbose_name='وضعیت انتشار')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انتشار')

    # Duration field for videos and audio (stored as DurationField)
    duration = models.DurationField(blank=True, null=True, verbose_name='مدت زمان')

    # File size in bytes
    file_size = models.PositiveBigIntegerField(blank=True, null=True, verbose_name='حجم فایل')

    # For text content - word count
    word_count = models.PositiveIntegerField(blank=True, null=True, verbose_name='تعداد کلمات')

    order = models.PositiveIntegerField(default=1, verbose_name='ترتیب')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'اپیزود'
        verbose_name_plural = 'اپیزودها'
        ordering = ['chapter', 'order']
        unique_together = ['course', 'order']
    
    def save(self, *args, **kwargs):
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_formatted_file_size(self):
        """Return human-readable file size"""
        if not self.file_size:
            return None

        # Convert bytes to appropriate unit
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.1f} TB"

    def get_formatted_duration(self):
        """Return human-readable duration"""
        if not self.duration:
            return None

        total_seconds = self.duration.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"



class RoadMap(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام نقشه راه')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='اسلاگ نقشه راه')
    description = models.TextField(verbose_name='توضیحات')
    courses = models.ManyToManyField(Course, related_name='roadmaps', verbose_name='دوره‌ها')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    cover_image = models.ImageField(verbose_name='تصویر نقشه راه', upload_to='roadmap_cover_image')
    
    status = models.CharField(max_length=20, choices=Course.PUBLISHED_STATUS, default='draft')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ انتشار')
    
    def __str__(self):
        return self.name
    
    def courses_count(self):
        """Return the number of courses in this roadmap"""
        return self.courses.count()
    
    def get_courses(self):
        """Return the published courses associated with this roadmap."""
        return self.courses.filter(status='published')
    
    def save(self, *args, **kwargs):
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = 'نقشه راه'
        verbose_name_plural = 'نقشه‌های راه'
        
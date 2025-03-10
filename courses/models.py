from django.db import models
from django.contrib.auth import get_user_model

from taxonomy.models import Category, Tag
from accounts.models import OrganizerProfile, TeacherProfile


class Attribute(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام ویژگی')
    value = models.CharField(max_length=255, verbose_name='مقدار ویژگی')

    def __str__(self):
        return f"{self.name}: {self.value}"

    class Meta:
        verbose_name = 'ویژگی'
        verbose_name_plural = 'ویژگی‌ها'


class Chapter(models.Model):
    number = models.PositiveSmallIntegerField(verbose_name='شماره فصل')
    title = models.CharField(max_length=100, verbose_name='عنوان فصل')
    description = models.TextField(blank=True, verbose_name='توضیحات فصل')

    def __str__(self):
        return f"فصل {self.number}: {self.title}"

    class Meta:
        verbose_name = 'فصل'
        verbose_name_plural = 'فصل‌ها'


class Course(models.Model):
    objects = models.Manager()

    cover_image = models.ImageField(verbose_name='تصویر دوره', upload_to='cover_image')
    title = models.CharField(max_length=100, verbose_name='تیتر دوره')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='اسلاگ دوره')
    description = models.TextField(verbose_name='توضیحات کامل دوره')
    price = models.DecimalField(max_digits=9, decimal_places=0, verbose_name='قیمت')
    intro_video_link = models.URLField(verbose_name='لینک ویدیو معرفی')
    total_hours = models.DecimalField(max_digits=5, decimal_places=1, verbose_name='مجموع ساعات')

    # Relationships
    organizers = models.ManyToManyField(OrganizerProfile, related_name='organized_courses', verbose_name='برگزار کنندگان')
    teachers = models.ManyToManyField(TeacherProfile, related_name='teaching_courses', verbose_name='مدرسین')
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
        
    def is_free_for_user(self, user):
        """Check if the course is free for a specific user via their subscriptions"""
        from django.utils import timezone
        return UserSubscription.objects.filter(
            user=user,
            is_active=True,
            end_date__gt=timezone.now(),
            subscription_plan__included_courses=self
        ).exists()


class Episode(models.Model):
    EPISODE_TYPES = (
        ('video', 'ویدیو'),
        ('file', 'فایل'),
        ('text', 'متن'),
        ('quiz', 'آزمون'),
    )

    title = models.CharField(max_length=200, verbose_name='عنوان اپیزود')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='اسلاگ اپیزود')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='episodes', verbose_name='فصل')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='episodes', verbose_name='دوره')
    type = models.CharField(max_length=10, choices=EPISODE_TYPES, default='video', verbose_name='نوع')
    thumbnail = models.ImageField(upload_to='episode_thumbnails', blank=True, null=True,
                                  verbose_name='تصویر بند انگشتی')
    content_url = models.URLField(verbose_name='آدرس محتوا')
    description = models.TextField(blank=True, verbose_name='توضیحات')

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

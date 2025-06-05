from django.db import models
from django.contrib.auth import get_user_model
from taxonomy.models import Category, Tag
from accounts.models import Author

User = get_user_model()


class Post(models.Model):
    title = models.CharField(max_length=200, verbose_name='عنوان')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='اسلاگ')
    content = models.TextField(verbose_name='محتوا')
    excerpt = models.TextField(blank=True, verbose_name='خلاصه')
    featured_image = models.ImageField(
        upload_to='blog/images/%Y/%m/%d/', blank=True, null=True, verbose_name='تصویر شاخص')

    # Taxonomy
    categories = models.ManyToManyField(
        Category,
        related_name='blog_posts',
        limit_choices_to={'content_type__in': ['blog', 'both']},
        verbose_name='دسته‌بندی‌ها',
        blank=True  # Allow posts to have no categories initially
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='blog_posts',
        limit_choices_to={'content_type__in': ['blog', 'both']},
        verbose_name='تگ‌ها',
        blank=True  # Allow posts to have no tags initially
    )

    # Author
    author = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,  # Or models.CASCADE if an author must exist
        null=True,  # Allow null if author can be deleted or not set
        related_name='blog_posts',
        verbose_name='نویسنده'
    )

    # Engagement Metrics
    views_count = models.PositiveIntegerField(
        default=0, verbose_name='تعداد بازدید')
    # Placeholder, actual liking mechanism needed
    likes_count = models.PositiveIntegerField(
        default=0, verbose_name='تعداد لایک‌ها')
    average_read_time = models.PositiveIntegerField(
        default=5, verbose_name='زمان متوسط مطالعه (دقیقه)')

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='تاریخ بروزرسانی')
    published_at = models.DateTimeField(
        blank=True, null=True, verbose_name='تاریخ انتشار')

    # Status
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('review', 'در بازبینی'),
        ('published', 'منتشر شده'),
    ]
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')

    class Meta:
        verbose_name = 'نوشته'
        verbose_name_plural = 'نوشته‌ها'
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def get_featured_image_url(self):
        if self.featured_image and hasattr(self.featured_image, 'url'):
            return self.featured_image.url
        return None  # Or a default placeholder image URL

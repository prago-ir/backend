from django.db import models
from django.contrib.auth import get_user_model
from taxonomy.models import Category, Tag
from accounts.models import AuthorProfile

User = get_user_model()

class Post(models.Model):
    title = models.CharField(max_length=200, verbose_name='عنوان')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='اسلاگ')
    content = models.TextField(verbose_name='محتوا')
    excerpt = models.TextField(blank=True, verbose_name='خلاصه')
    featured_image = models.ImageField(upload_to='blog/images', blank=True, null=True, verbose_name='تصویر شاخص')
    
    # Taxonomy
    categories = models.ManyToManyField(Category, related_name='blog_posts', 
                                      limit_choices_to={'content_type__in': ['blog', 'both']},
                                      verbose_name='دسته‌بندی‌ها')
    tags = models.ManyToManyField(Tag, related_name='blog_posts',
                                limit_choices_to={'content_type__in': ['blog', 'both']},
                                verbose_name='تگ‌ها')
    
    # Author
    author = models.ForeignKey(AuthorProfile, on_delete=models.CASCADE, 
                             related_name='blog_posts', verbose_name='نویسنده')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    published_at = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ انتشار')
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('review', 'در بازبینی'),
        ('published', 'منتشر شده'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='وضعیت')
    
    class Meta:
        verbose_name = 'نوشته'
        verbose_name_plural = 'نوشته‌ها'
        ordering = ['-published_at']
        
        

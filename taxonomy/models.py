from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام دسته‌بندی')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='اسلاگ دسته‌بندی')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, 
                              related_name='children', verbose_name='دسته‌بندی والد')
    content_type = models.CharField(max_length=20, choices=[
        ('course', 'دوره'),
        ('blog', 'بلاگ'),
        ('both', 'هردو')
    ], default='both', verbose_name='نوع محتوا')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'


class Tag(models.Model):
    name = models.CharField(max_length=50, verbose_name='نام تگ')
    slug = models.SlugField(max_length=50, unique=True, verbose_name='اسلاگ تگ')
    content_type = models.CharField(max_length=20, choices=[
        ('course', 'دوره'),
        ('blog', 'بلاگ'),
        ('both', 'هردو')
    ], default='both', verbose_name='نوع محتوا')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'تگ'
        verbose_name_plural = 'تگ‌ها'
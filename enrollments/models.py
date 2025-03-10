from django.db import models
from django.contrib.auth import get_user_model

from courses.models import Course

User = get_user_model()

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments', verbose_name='کاربر')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments', verbose_name='دوره')
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت نام')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    last_accessed_at = models.DateTimeField(blank=True, null=True, verbose_name='آخرین دسترسی')
    completion_percentage = models.PositiveSmallIntegerField(default=0, verbose_name='درصد تکمیل')

    class Meta:
        verbose_name = 'ثبت نام'
        verbose_name_plural = 'ثبت نام‌ها'
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

    @classmethod
    def get_enrollment_count(cls, course_id):
        return cls.objects.filter(course_id=course_id, is_active=True).count()
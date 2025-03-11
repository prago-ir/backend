from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from courses.models import Course, Episode

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
    
    def update_last_accessed(self):
        """Update the last accessed timestamp to current time"""
        self.last_accessed_at = timezone.now()
        self.save(update_fields=['last_accessed_at'])
    
    def update_completion_percentage(self):
        """Calculate and update the completion percentage based on completed episodes"""
        total_episodes = self.course.episodes.count()
        if total_episodes == 0:
            self.completion_percentage = 0
            self.save(update_fields=['completion_percentage'])
            return
            
        completed_episodes = UserProgress.objects.filter(
            user=self.user,
            episode__course=self.course,
            completed=True
        ).count()
        
        self.completion_percentage = int((completed_episodes / total_episodes) * 100)
        self.save(update_fields=['completion_percentage'])


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress', verbose_name='کاربر')
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='user_progress', verbose_name='اپیزود')
    completed = models.BooleanField(default=False, verbose_name='تکمیل شده')
    progress_percentage = models.PositiveSmallIntegerField(default=0, verbose_name='درصد پیشرفت')
    last_position = models.PositiveIntegerField(default=0, verbose_name='آخرین موقعیت')  # For videos, in seconds
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='تاریخ تکمیل')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاریخ بروزرسانی')
    
    class Meta:
        verbose_name = 'پیشرفت کاربر'
        verbose_name_plural = 'پیشرفت‌های کاربر'
        unique_together = ['user', 'episode']
    
    def __str__(self):
        return f"{self.user.username} - {self.episode.title} - {self.progress_percentage}%"
    
    def mark_as_completed(self):
        """Mark episode as completed and update completion_at timestamp"""
        if not self.completed:
            self.completed = True
            self.progress_percentage = 100
            self.completed_at = timezone.now()
            self.save(update_fields=['completed', 'progress_percentage', 'completed_at'])
            
            # Update enrollment completion percentage
            enrollment = Enrollment.objects.get(user=self.user, course=self.episode.course)
            enrollment.update_completion_percentage()
    
    def update_progress(self, position, duration):
        """Update progress based on current position in video"""
        if duration > 0:
            self.last_position = position
            self.progress_percentage = min(int((position / duration) * 100), 100)
            
            # If progress is > 90%, mark as completed
            if self.progress_percentage > 90 and not self.completed:
                self.mark_as_completed()
            else:
                self.save(update_fields=['last_position', 'progress_percentage'])
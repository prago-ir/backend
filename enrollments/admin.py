from django.contrib import admin
from .models import Enrollment, UserProgress

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at', 'is_active', 'completion_percentage')
    list_filter = ('is_active', 'enrolled_at')
    search_fields = ('user__username', 'user__email', 'course__title')
    readonly_fields = ('enrolled_at', 'last_accessed_at', 'completion_percentage')
    date_hierarchy = 'enrolled_at'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'course')
        }),
        ('Status Information', {
            'fields': ('is_active', 'completion_percentage')
        }),
        ('Timestamps', {
            'fields': ('enrolled_at', 'last_accessed_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'episode', 'progress_percentage', 'completed', 'updated_at')
    list_filter = ('completed', 'created_at')
    search_fields = ('user__username', 'user__email', 'episode__title')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    
    fieldsets = (
        ('User and Episode', {
            'fields': ('user', 'episode')
        }),
        ('Progress Information', {
            'fields': ('completed', 'progress_percentage', 'last_position')
        }),
        ('Timestamps', {
            'fields': ('completed_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

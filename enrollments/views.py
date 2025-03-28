from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Enrollment
from courses.models import Course
from subscriptions.models import UserSubscription

class EnrollmentListView(APIView):
    """
    View for listing a user's course enrollments
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        enrollments = Enrollment.objects.filter(user=request.user, is_active=True).order_by('-enrollment_date')
        
        enrollment_list = []
        for enrollment in enrollments:
            course = enrollment.course
            # Calculate progress if applicable
            progress = 0
            completed_lessons = 0
            total_lessons = course.lessons.count() if hasattr(course, 'lessons') else 0
            
            if hasattr(enrollment, 'progress'):
                completed_lessons = enrollment.progress.completed_lessons.count()
                progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0
            
            # Get enrollment source (direct purchase or subscription)
            enrollment_source = "direct_purchase"
            subscription_id = None
            
            # Check if this enrollment is from a subscription
            active_subscriptions = UserSubscription.objects.filter(
                user=request.user,
                is_active=True,
                subscription_plan__included_courses=course
            )
            
            if active_subscriptions.exists():
                enrollment_source = "subscription"
                subscription_id = active_subscriptions.first().id
            
            enrollment_data = {
                'id': enrollment.id,
                'course': {
                    'id': course.id,
                    'title': course.title,
                    'slug': course.slug if hasattr(course, 'slug') else None,
                    'image': course.thumbnail.url if hasattr(course, 'thumbnail') and course.thumbnail else None,
                    'instructor': course.instructor.user.get_full_name() if hasattr(course, 'instructor') and course.instructor else None
                },
                'enrollment_date': enrollment.enrollment_date.isoformat(),
                'is_active': enrollment.is_active,
                'progress': progress,
                'completed_lessons': completed_lessons,
                'total_lessons': total_lessons,
                'enrollment_source': enrollment_source,
                'subscription_id': subscription_id
            }
            
            enrollment_list.append(enrollment_data)
        
        return Response(enrollment_list)

class EnrollmentDetailView(APIView):
    """
    View for retrieving details of a specific enrollment
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_slug):
        course = get_object_or_404(Course, slug=course_slug)
        enrollment = get_object_or_404(Enrollment, user=request.user, course=course, is_active=True)
        
        # Calculate detailed progress
        progress_data = {}
        total_lessons = course.lessons.count() if hasattr(course, 'lessons') else 0
        completed_lessons = 0
        
        if hasattr(enrollment, 'progress'):
            completed_lessons = enrollment.progress.completed_lessons.count()
            last_accessed = enrollment.progress.last_accessed_lesson
            
            # Get completed chapters/sections
            if hasattr(course, 'sections'):
                sections_progress = []
                for section in course.sections.all():
                    section_lessons = section.lessons.count()
                    section_completed = enrollment.progress.completed_lessons.filter(section=section).count()
                    
                    section_data = {
                        'id': section.id,
                        'title': section.title,
                        'total_lessons': section_lessons,
                        'completed_lessons': section_completed,
                        'progress_percentage': int((section_completed / section_lessons) * 100) if section_lessons > 0 else 0
                    }
                    sections_progress.append(section_data)
                
                progress_data['sections'] = sections_progress
            
            progress_data['last_accessed_lesson'] = {
                'id': last_accessed.id,
                'title': last_accessed.title
            } if last_accessed else None
        
        # Get enrollment source (direct purchase or subscription)
        enrollment_source = "direct_purchase"
        subscription_data = None
        
        # Check if this enrollment is from a subscription
        active_subscriptions = UserSubscription.objects.filter(
            user=request.user,
            is_active=True,
            subscription_plan__included_courses=course
        )
        
        if active_subscriptions.exists():
            subscription = active_subscriptions.first()
            enrollment_source = "subscription"
            
            # Calculate subscription remaining time
            now = timezone.now()
            remaining_days = (subscription.end_date - now).days if subscription.end_date > now else 0
            
            subscription_data = {
                'id': subscription.id,
                'plan_name': subscription.subscription_plan.name,
                'end_date': subscription.end_date.isoformat(),
                'remaining_days': remaining_days,
                'is_valid': subscription.is_valid()
            }
        
        # Get related order if available
        order_data = None
        if enrollment_source == "direct_purchase" and hasattr(course, 'orders'):
            order = course.orders.filter(user=request.user, status='paid').first()
            if order:
                order_data = {
                    'order_number': order.order_number,
                    'paid_at': order.paid_at.isoformat() if order.paid_at else None,
                    'amount': float(order.final_amount)
                }
        
        enrollment_data = {
            'id': enrollment.id,
            'course': {
                'id': course.id,
                'title': course.title,
                'slug': course.slug if hasattr(course, 'slug') else None,
                'description': course.description if hasattr(course, 'description') else None,
                'image': course.thumbnail.url if hasattr(course, 'thumbnail') and course.thumbnail else None,
                'instructor': course.instructor.user.get_full_name() if hasattr(course, 'instructor') and course.instructor else None
            },
            'enrollment_date': enrollment.enrollment_date.isoformat(),
            'is_active': enrollment.is_active,
            'progress_percentage': int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0,
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons,
            'progress': progress_data,
            'enrollment_source': enrollment_source,
            'subscription': subscription_data,
            'order': order_data
        }
        
        return Response(enrollment_data)

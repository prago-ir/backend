from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Case, When, Value, IntegerField
from django.utils import timezone

from .models import Course, Episode
from .serializers import CourseSerializer, CourseDetailSerializer, EpisodeSerializer
from enrollments.models import Enrollment, UserProgress

class LatestCoursesView(APIView):
    """View to get the last six published courses for home page"""
    
    def get(self, request):
        # Get last 6 published courses ordered by published date
        queryset = Course.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).order_by('-published_at')[:6]
        
        serializer = CourseSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PopularCoursesView(APIView):
    """View to get the most popular courses"""
    
    def get(self, request):
        # Get popular courses ordered by enrollment count
        queryset = Course.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).annotate(enrollment_count=Count('enrollments')).order_by('-enrollment_count')[:6]
        
        serializer = CourseSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


class CourseListView(APIView):
    def get(self, request):
        queryset = Course.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        )

        # Search functionality
        search_query = request.query_params.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(latin_title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(teachers__first_name__icontains=search_query) |
                Q(teachers__last_name__icontains=search_query)
            ).distinct()

        # Filtering
        types = request.query_params.getlist('types')
        duration = request.query_params.getlist('duration')
        organizer = request.query_params.getlist('organizer')
        category = request.query_params.getlist('category')

        if types:
            queryset = queryset.filter(type__in=types)
        if duration:
            queryset = queryset.filter(duration__in=duration)
        if organizer:
            queryset = queryset.filter(organizers__id__in=organizer)
        if category:
            queryset = queryset.filter(categories__id__in=category)

        # Sorting
        sort_option = request.query_params.get('sort', 'newest')
        if sort_option == 'newest':
            queryset = queryset.order_by('-published_at')
        elif sort_option == 'popular':
            queryset = queryset.annotate(enrollment_count=Count('enrollments')).order_by('-enrollment_count')
        elif sort_option == 'priceLow':
            queryset = queryset.order_by('price')
        elif sort_option == 'priceHigh':
            queryset = queryset.order_by('-price')
        elif sort_option == 'ratingHigh':
            queryset = queryset.order_by('-rating')

        serializer = CourseSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CourseDetailView(APIView):
    """View to get course details and related courses"""
    
    def get(self, request, slug):
        # Get the course by slug
        course = get_object_or_404(
            Course, 
            slug=slug, 
            status='published',
            published_at__lte=timezone.now()
        )
        
        # Get related courses (from same category, same teacher, or similar tags)
        related_courses = Course.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).exclude(id=course.id)
        
        # Prioritize courses with same category, then same teacher, then same tags
        related_courses = related_courses.annotate(
            relevance_score=Case(
                When(categories__in=course.categories.all(), then=Value(3)),
                When(teachers__in=course.teachers.all(), then=Value(2)),
                When(tags__in=course.tags.all(), then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).filter(relevance_score__gt=0).order_by('-relevance_score', '-published_at').distinct()[:3]
        
        # Check if user is enrolled in this course
        is_enrolled = False
        if request.user.is_authenticated:
            is_enrolled = Enrollment.objects.filter(
                user=request.user, 
                course=course,
                is_active=True
            ).exists()
        
        # Serialize course data
        serializer = CourseDetailSerializer(course, context={'is_enrolled': is_enrolled})
        
        # Serialize related courses
        related_serializer = CourseSerializer(related_courses, many=True)
        
        return Response({
            'course': serializer.data,
            'related_courses': related_serializer.data
        }, status=status.HTTP_200_OK)


class OwnedCoursesView(APIView):
    """View to list courses owned by the authenticated user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get user's active enrollments
        enrollments = Enrollment.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('course')
        
        # Extract courses from enrollments
        courses = [enrollment.course for enrollment in enrollments]
        
        # Add enrollment data to each course
        course_data = []
        for course, enrollment in zip(courses, enrollments):
            course_serializer = CourseSerializer(course)
            data = course_serializer.data
            data['enrollment'] = {
                'enrolled_at': enrollment.enrolled_at,
                'last_accessed_at': enrollment.last_accessed_at,
                'completion_percentage': enrollment.completion_percentage
            }
            course_data.append(data)
        
        return Response(course_data, status=status.HTTP_200_OK)


class DashboardCourseDetailView(APIView):
    """View for course details in user dashboard with episode progress"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, slug):
        # Get course by slug
        course = get_object_or_404(Course, slug=slug)
        
        # Check if user is enrolled
        enrollment = get_object_or_404(
            Enrollment, 
            user=request.user, 
            course=course,
            is_active=True
        )
        
        # Update last accessed time
        enrollment.update_last_accessed()
        
        # Get all episodes with progress info
        episodes = Episode.objects.filter(
            course=course,
            status='published'
        ).order_by('chapter__number', 'order')
        
        # Group episodes by chapter
        chapters_data = {}
        for episode in episodes:
            chapter_id = episode.chapter.id
            
            # Get progress for this episode
            progress, created = UserProgress.objects.get_or_create(
                user=request.user,
                episode=episode,
                defaults={
                    'progress_percentage': 0,
                    'last_position': 0,
                    'completed': False
                }
            )
            
            # Prepare episode data with progress
            episode_data = EpisodeSerializer(episode).data
            episode_data.update({
                'progress': {
                    'percentage': progress.progress_percentage,
                    'last_position': progress.last_position,
                    'completed': progress.completed,
                    'completed_at': progress.completed_at
                }
            })
            
            # Add to chapter data structure
            if chapter_id not in chapters_data:
                chapters_data[chapter_id] = {
                    'id': episode.chapter.id,
                    'title': episode.chapter.title,
                    'number': episode.chapter.number,
                    'episodes': []
                }
            
            chapters_data[chapter_id]['episodes'].append(episode_data)
        
        # Convert to list and sort by chapter number
        chapters = list(chapters_data.values())
        chapters.sort(key=lambda x: x['number'])
        
        # Prepare course data
        course_serializer = CourseDetailSerializer(course)
        response_data = course_serializer.data
        response_data.update({
            'chapters': chapters,
            'enrollment': {
                'enrolled_at': enrollment.enrolled_at,
                'last_accessed_at': enrollment.last_accessed_at,
                'completion_percentage': enrollment.completion_percentage
            }
        })
        
        return Response(response_data, status=status.HTTP_200_OK)


class CourseEnrollmentView(APIView):
    """View to handle course enrollment/ownership"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, slug):
        course = get_object_or_404(
            Course,
            slug=slug,
            status='published',
            published_at__lte=timezone.now()
        )
        
        # Check if already enrolled
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"detail": "You are already enrolled in this course."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if course is free for this user via subscription
        is_free = course.is_free_for_user(request.user)
        
        # If not free, this would typically redirect to payment
        # But for this endpoint, we'll just create the enrollment
        # In a real system, you'd handle payment before creating enrollment
        
        # Create enrollment
        enrollment = Enrollment.objects.create(
            user=request.user,
            course=course,
            is_active=True
        )
        
        return Response({
            "detail": "Successfully enrolled in course",
            "enrollment_id": enrollment.id,
            "enrolled_at": enrollment.enrolled_at,
        }, status=status.HTTP_201_CREATED)


class UpdateProgressView(APIView):
    """View to update user progress on an episode"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, episode_id):
        episode = get_object_or_404(Episode, id=episode_id)
        
        # Check if user is enrolled in the course
        get_object_or_404(
            Enrollment,
            user=request.user,
            course=episode.course,
            is_active=True
        )
        
        # Get or create progress
        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            episode=episode
        )
        
        # Update progress from request data
        position = request.data.get('position', 0)
        duration = request.data.get('duration', 0)
        completed = request.data.get('completed', False)
        
        if completed:
            progress.mark_as_completed()
        elif duration > 0:
            progress.update_progress(position, duration)
        
        return Response({
            'progress_percentage': progress.progress_percentage,
            'completed': progress.completed
        }, status=status.HTTP_200_OK)
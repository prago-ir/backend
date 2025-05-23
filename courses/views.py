from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny  # Import AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Case, When, Value, IntegerField
from django.utils import timezone

from .models import Course, Episode, RoadMap
from .serializers import CourseSerializer, CourseDetailSerializer, EpisodeSerializer, RoadMapSerializer
from enrollments.models import Enrollment, UserProgress
from taxonomy.serializers import CategorySerializer
from accounts.serializers import OrganizerSerializer
from subscriptions.models import UserSubscription  # Add this import


class LatestRoadmapView(APIView):
    """View to get the last three published roadmaps for home page"""
    permission_classes = [AllowAny]  # Add this line to allow public access

    def get(self, request):
        queryset = RoadMap.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).order_by('-published_at')[:3]

        serializer = RoadMapSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LatestCoursesView(APIView):
    """View to get the last six published courses for home page"""
    permission_classes = [AllowAny]  # Add this line to allow public access

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
    permission_classes = [AllowAny]  # Add this line to allow public access

    def get(self, request):
        # Get popular courses ordered by enrollment count
        queryset = Course.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).annotate(enrollment_count=Count('enrollments')).order_by('-enrollment_count')[:6]

        serializer = CourseSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CourseListView(APIView):
    permission_classes = [AllowAny]  # Add this line to allow public access

    def get(self, request):
        # Get all published courses
        courses_queryset = Course.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        )

        # Add any essential annotations that will be needed for sorting on frontend
        courses_queryset = courses_queryset.annotate(
            enrollment_count=Count('enrollments')
        )

        # Include related data to avoid N+1 queries
        courses_queryset = courses_queryset.prefetch_related(
            'teachers', 'categories', 'organizers', 'tags'
        )

        # Get all published roadmaps
        roadmaps_queryset = RoadMap.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        )

        # Prefetch related courses for roadmaps
        roadmaps_queryset = roadmaps_queryset.prefetch_related('courses')

        # Serialize both types of content
        courses_serializer = CourseSerializer(courses_queryset, many=True)
        roadmaps_serializer = RoadMapSerializer(roadmaps_queryset, many=True)

        # Prepare metadata needed for filtering
        unique_categories = set()
        for course in courses_queryset:
            for category in course.categories.all():
                unique_categories.add(category)

        unique_organizers = set()
        for course in courses_queryset:
            for org in course.organizers.all():
                unique_organizers.add(org)

        # Serialize the metadata
        categories_data = CategorySerializer(unique_categories, many=True).data
        organizers_data = OrganizerSerializer(
            unique_organizers, many=True).data

        # Add content type information to each item
        courses_data = courses_serializer.data
        for course in courses_data:
            course['content_type'] = 'course'

        roadmaps_data = roadmaps_serializer.data
        for roadmap in roadmaps_data:
            roadmap['content_type'] = 'roadmap'

        # Combine courses and roadmaps into a single list
        combined_content = courses_data + roadmaps_data

        return Response({
            'content': combined_content,
            'metadata': {
                'categories': categories_data,
                'organizers': organizers_data,
                'types': ['course', 'roadmap']
            }
        }, status=status.HTTP_200_OK)


class CourseDetailView(APIView):
    """View to get course details and related courses"""
    permission_classes = [AllowAny]  # Add this line to allow public access

    def get(self, request, slug):
        # Get the course by slug
        course = get_object_or_404(
            Course,
            slug=slug,
            status='published',
            published_at__lte=timezone.now()
        )

        chapters_data = {}
        episodes = Episode.objects.filter(
            course=course, status='published').order_by('chapter__number', 'order')

        for episode in episodes:
            chapter_id = episode.chapter.id

            episode_serializer = EpisodeSerializer(
                episode, context={'request': request})

            if chapter_id not in chapters_data:
                chapters_data[chapter_id] = {
                    'id': episode.chapter.id,
                    'title': episode.chapter.title,
                    'number': episode.chapter.number,
                    'episodes': []
                }
            chapters_data[chapter_id]['episodes'].append(
                episode_serializer.data)

        # Convert to list and sort by chapter number
        chapter_list = list(chapters_data.values())
        chapter_list.sort(key=lambda x: x['number'])

        # Get related courses (same category, same teacher, or similar tags)
        related_courses = Course.objects.filter(
            Q(categories__in=course.categories.all()) |
            Q(teachers__in=course.teachers.all()) |
            Q(tags__in=course.tags.all()),
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
        active_granting_subscription_data = None  # Initialize

        if request.user.is_authenticated:
            is_enrolled = Enrollment.objects.filter(
                user=request.user,
                course=course,
                is_active=True
            ).exists()

            # Find active subscription that grants access to THIS course
            granting_subscription = UserSubscription.objects.filter(
                user=request.user,
                is_active=True,
                end_date__gt=timezone.now(),
                subscription_plan__included_courses=course
            ).order_by('-end_date').first()  # Get the one that ends latest

            if granting_subscription:
                now = timezone.now()
                remaining_days = (granting_subscription.end_date -
                                  now).days if granting_subscription.end_date > now else 0
                active_granting_subscription_data = {
                    'plan_name': granting_subscription.subscription_plan.name,
                    'end_date': granting_subscription.end_date.isoformat(),
                    'remaining_days': remaining_days,
                    'plan_slug': granting_subscription.subscription_plan.slug
                }

        # Serialize course data
        serializer = CourseDetailSerializer(
            # Ensure request is in context
            course, context={'request': request, 'is_enrolled': is_enrolled})

        # Serialize related courses
        related_serializer = CourseSerializer(related_courses, many=True)

        course_response_data = serializer.data
        course_response_data.update({
            'chapters': chapter_list,
        })

        response_payload = {
            'course': course_response_data,
            'related_courses': related_serializer.data
        }

        if active_granting_subscription_data:
            response_payload['active_granting_subscription'] = active_granting_subscription_data

        return Response(response_payload, status=status.HTTP_200_OK)


class OwnedCoursesView(APIView):
    """View to list courses owned by the authenticated user"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get user's active enrollments
        enrollments = Enrollment.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('course')

        course_data = []
        for enrollment in enrollments:
            course = enrollment.course
            item_data = {
                'course': {
                    'cover_image_url': course.cover_image.url if course.cover_image else None,
                    'title': course.title,
                    'slug': course.slug,
                },
                'enrollment': {
                    'enrolled_at': enrollment.enrolled_at.isoformat(),
                    'last_accessed_at': enrollment.last_accessed_at.isoformat() if enrollment.last_accessed_at else None,
                    'completion_percentage': enrollment.completion_percentage
                }
            }
            course_data.append(item_data)

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
            # Ensure published_at is not in the future if you use it as a gate
            # published_at__lte=timezone.now() # This line can be strict, consider if needed
        )

        # Check if already enrolled
        existing_enrollment = Enrollment.objects.filter(
            user=request.user, course=course).first()
        if existing_enrollment:
            if not existing_enrollment.is_active:  # Ensure enrollment is active
                existing_enrollment.is_active = True
                existing_enrollment.save(update_fields=['is_active'])
            return Response({
                "detail": "User is already enrolled in this course.",
                "enrollment_id": existing_enrollment.id,
                "enrolled_at": existing_enrollment.enrolled_at.isoformat(),
            }, status=status.HTTP_200_OK)

        # Check if course is accessible for free for this user (e.g., via subscription)
        # The model method course.is_free_for_user(request.user) checks this
        if not course.is_free_for_user(request.user):
            return Response(
                {"detail": "Course access not granted. Subscription required or course is not part of an active subscription."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create enrollment if accessible and not yet enrolled
        enrollment = Enrollment.objects.create(
            user=request.user,
            course=course,
            is_active=True
        )

        return Response({
            "detail": "Successfully enrolled in course",
            "enrollment_id": enrollment.id,
            "enrolled_at": enrollment.enrolled_at.isoformat(),
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

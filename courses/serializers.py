from rest_framework import serializers

from accounts.serializers import OrganizerSerializer, TeacherSerializer
from taxonomy.serializers import CategorySerializer, TagSerializer
from .models import Course, Episode, Chapter, Attribute, RoadMap
from enrollments.models import Enrollment
from subscriptions.models import UserSubscription  # Add this import
from django.utils import timezone  # Add this import


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ['id', 'name', 'value', 'icon']


class EpisodeSerializer(serializers.ModelSerializer):
    duration_formatted = serializers.SerializerMethodField()
    file_size_formatted = serializers.SerializerMethodField()
    is_free = serializers.SerializerMethodField()
    content_url = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = ['id', 'title', 'type', 'thumbnail', 'content_url', 'description',
                  'duration', 'duration_formatted', 'file_size', 'file_size_formatted',
                  'order', 'status', 'published_at', 'is_free']

    def get_duration_formatted(self, obj):
        return obj.get_formatted_duration()

    def get_file_size_formatted(self, obj):
        return obj.get_formatted_file_size()

    def get_is_free(self, obj):
        # Get the first two episodes by order from this course
        first_two_episodes = Episode.objects.filter(
            course=obj.course,
            status='published',
            type='video'
        ).order_by('order')[:2]

        # Check if current episode is one of the first two
        return obj in first_two_episodes

    def get_content_url(self, obj):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None

        # Get the first two episodes by order from this course
        first_two_episodes = Episode.objects.filter(
            course=obj.course,
            status='published',
            type='video'
        ).order_by('order')[:2]

        # If episode is free (first two), always show content URL
        if obj in first_two_episodes:
            return obj.content_url

        # If user is authenticated, check for access
        if user and user.is_authenticated:
            # Check if user has purchased this course (direct enrollment)
            has_direct_enrollment = Enrollment.objects.filter(
                user=user,
                course=obj.course,
                is_active=True
            ).exists()

            if has_direct_enrollment:
                return obj.content_url

            # Check if user has an active subscription that includes this course
            has_subscription_access = UserSubscription.objects.filter(
                user=user,
                is_active=True,
                end_date__gt=timezone.now(),
                subscription_plan__included_courses=obj.course  # obj is an Episode instance
            ).exists()

            if has_subscription_access:
                return obj.content_url

        # Otherwise, don't provide the content URL
        return None


class ChapterSerializer(serializers.ModelSerializer):
    episodes = EpisodeSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'number', 'title', 'description', 'episodes']


class CourseSerializer(serializers.ModelSerializer):
    teachers = TeacherSerializer(many=True, read_only=True)
    organizers = OrganizerSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    attributes = AttributeSerializer(many=True, read_only=True)
    current_price = serializers.SerializerMethodField()
    has_special_offer = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'latin_title', 'slug', 'cover_image', 'description', 'price',
                  'current_price', 'has_special_offer', 'special_offer_price',
                  'total_hours', 'published_at', 'teachers', 'organizers', 'categories', 'attributes', 'status']

    def get_current_price(self, obj):
        return obj.get_current_price()

    def get_has_special_offer(self, obj):
        return obj.has_active_special_offer()


class CourseDetailSerializer(serializers.ModelSerializer):
    teachers = TeacherSerializer(many=True, read_only=True)
    organizers = OrganizerSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    attributes = AttributeSerializer(many=True, read_only=True)
    chapters = ChapterSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    has_special_offer = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    is_accessible_via_subscription = serializers.SerializerMethodField()  # New field

    class Meta:
        model = Course
        fields = ['id', 'title', 'latin_title', 'slug', 'cover_image_url', 'description',
                  'price', 'current_price', 'has_special_offer', 'special_offer_price',
                  'special_offer_start_date', 'special_offer_end_date', 'intro_video_link',
                  'total_hours', 'published_at', 'teachers', 'organizers',
                  'categories', 'tags', 'attributes', 'chapters', 'status',
                  'is_enrolled', 'is_accessible_via_subscription']  # Added new field

    def get_cover_image_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None

    def get_current_price(self, obj):
        return obj.get_current_price()

    def get_has_special_offer(self, obj):
        return obj.has_active_special_offer()

    def get_is_enrolled(self, obj):
        # Check if context contains enrollment info
        return self.context.get('is_enrolled', False)

    def get_is_accessible_via_subscription(self, obj):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None
        if user and user.is_authenticated:
            return obj.is_free_for_user(user)  # Uses the existing model method
        return False


class RoadMapSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()
    total_hours = serializers.SerializerMethodField()
    total_videos = serializers.SerializerMethodField()

    class Meta:
        model = RoadMap
        fields = [
            'id', 'name', 'slug', 'description', 'cover_image',
            'status', 'published_at', 'courses', 'total_hours', 'total_videos'
        ]

    def get_courses(self, obj):
        # Only return published courses in the roadmap
        published_courses = obj.get_courses()
        return CourseSerializer(published_courses, many=True).data

    def get_total_hours(self, obj):
        # Calculate total hours from all courses in the roadmap
        published_courses = obj.get_courses()
        total = sum(course.total_hours or 0 for course in published_courses)
        return round(total, 1)  # Round to one decimal place

    def get_total_videos(self, obj):
        # Count all episodes from courses in this roadmap
        published_courses = obj.get_courses()
        count = 0
        for course in published_courses:
            # Count published episodes in each course
            count += Episode.objects.filter(
                course=course,
                status='published'
            ).count()
        return count

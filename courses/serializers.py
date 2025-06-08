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
    content_url = serializers.SerializerMethodField()
    is_free = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = [
            'id', 'title', 'description', 'type', 'order',
            'duration', 'file_size', 'thumbnail', 'content_url',
            'status', 'published_at', 'chapter', 'course', 'is_free'
        ]
        read_only_fields = ['order', 'is_free']

    def get_is_free(self, obj):
        # Determine if the episode is one of the first two free ones
        first_two_episodes = Episode.objects.filter(
            course=obj.course,
            status='published',
            # Consider if 'type' filter is needed here, e.g., only 'video'
            type='video',
            # Order by chapter then episode order
        ).order_by('chapter__number', 'order')[:2]

        # Create a list of IDs for efficient checking
        first_two_episode_ids = [ep.id for ep in first_two_episodes]
        return obj.id in first_two_episode_ids

    def get_content_url(self, obj):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None

        # Use the is_free logic from get_is_free
        if self.get_is_free(obj):
            return obj.content_url

        # If user is authenticated, check for subscription access
        if user and user.is_authenticated:
            # Check if user has an active subscription that includes this course
            has_subscription_access = UserSubscription.objects.filter(
                user=user,
                is_active=True,
                end_date__gt=timezone.now(),
                subscription_plan__included_courses=obj.course  # obj is an Episode instance
            ).exists()

            if has_subscription_access:
                return obj.content_url

        # Otherwise, (not free, not authenticated, or no subscription access)
        # don't provide the content URL
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
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'latin_title', 'slug', 'cover_image_url', 'description', 'excerpt',
                  'total_hours', 'published_at', 'teachers', 'organizers', 'categories', 'attributes', 'status']

    def get_cover_image_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None


class CourseDetailSerializer(serializers.ModelSerializer):
    teachers = TeacherSerializer(many=True, read_only=True)
    organizers = OrganizerSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    attributes = AttributeSerializer(many=True, read_only=True)
    chapters = ChapterSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    is_accessible_via_subscription = serializers.SerializerMethodField()  # New field

    class Meta:
        model = Course
        fields = ['id', 'title', 'latin_title', 'slug', 'cover_image_url', 'description', 'excerpt', 'intro_video_link',
                  'total_hours', 'published_at', 'teachers', 'organizers',
                  'categories', 'tags', 'attributes', 'chapters', 'status',
                  'is_enrolled', 'is_accessible_via_subscription']  # Added new field

    def get_cover_image_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None

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
    cover_image_url = serializers.SerializerMethodField()
    courses_count = serializers.SerializerMethodField()  # New field

    class Meta:
        model = RoadMap
        fields = [
            'id', 'name', 'slug', 'description', 'cover_image_url',
            'status', 'published_at', 'courses', 'total_hours', 'total_videos',
            'courses_count'  # Added new field
        ]

    def get_cover_image_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None

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

    def get_courses_count(self, obj):  # New method
        return obj.courses_count()


class CourseLiteSerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'cover_image_url']

    def get_cover_image_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url
        return None

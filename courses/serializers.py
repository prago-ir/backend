from rest_framework import serializers

from accounts.serializers import OrganizerSerializer, TeacherSerializer
from taxonomy.serializers import CategorySerializer, TagSerializer
from .models import Course, Episode, Chapter, Attribute, RoadMap
from enrollments.models import Enrollment


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ['id', 'name', 'value']



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
        # everything is not free
        return obj.order <= 2
    
    
    def get_content_url(self, obj):
        request = self.context.get('request')
        user = request.user if request and hasattr(request, 'user') else None
        
        # If episode is free (first two), always show content URL
        if obj.order <= 2:
            return obj.content_url
            
        # If user is authenticated, check if they have access
        if user and user.is_authenticated:
            # Check if user has purchased this course or has valid subscription
            has_access = Enrollment.objects.filter(
                user=user, 
                course=obj.course, 
                is_active=True
            ).exists()
            
            if has_access:
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
        fields = ['id', 'title', 'latin_title', 'slug', 'cover_image', 'description','price', 
                  'current_price', 'has_special_offer', 'special_offer_price',
                  'total_hours', 'published_at', 'teachers', 'organizers', 'categories', 'attributes','status']
    
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
    current_price = serializers.SerializerMethodField()
    has_special_offer = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'latin_title', 'slug', 'cover_image', 'description',
                  'price', 'current_price', 'has_special_offer', 'special_offer_price',
                  'special_offer_start_date', 'special_offer_end_date', 'intro_video_link',
                  'total_hours', 'published_at', 'teachers', 'organizers', 
                  'categories', 'tags', 'attributes', 'chapters', 'status', 'is_enrolled']
    
    def get_current_price(self, obj):
        return obj.get_current_price()
    
    def get_has_special_offer(self, obj):
        return obj.has_active_special_offer()
    
    def get_is_enrolled(self, obj):
        # Check if context contains enrollment info
        return self.context.get('is_enrolled', False)


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


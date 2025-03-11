from rest_framework import serializers
from .models import Course, Episode, Chapter, Attribute
from taxonomy.serializers import CategorySerializer, TagSerializer
from accounts.serializers import OrganizerSerializer, TeacherSerializer


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ['id', 'name', 'value']


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ['id', 'number', 'title', 'description']

class EpisodeSerializer(serializers.ModelSerializer):
    formatted_duration = serializers.SerializerMethodField()
    formatted_file_size = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = [
            'id', 'title', 'slug', 'type', 'thumbnail', 'content_url',
            'description', 'duration', 'formatted_duration', 
            'file_size', 'formatted_file_size', 'order'
        ]

    def get_formatted_duration(self, obj):
        return obj.get_formatted_duration()

    def get_formatted_file_size(self, obj):
        return obj.get_formatted_file_size()


class CourseSerializer(serializers.ModelSerializer):
    organizers = OrganizerSerializer(many=True, read_only=True)
    teachers = TeacherSerializer(many=True, read_only=True)
    attributes = AttributeSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    has_special_offer = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'cover_image', 'title', 'slug', 'description',
            'price', 'special_offer_price', 'special_offer_start_date', 
            'special_offer_end_date', 'has_special_offer', 'current_price',
            'intro_video_link', 'total_hours',
            'organizers', 'teachers', 'attributes', 'tags', 
            'categories', 'created_at', 'updated_at'
        ]
    
    def get_has_special_offer(self, obj):
        return obj.has_active_special_offer()
    
    def get_current_price(self, obj):
        return obj.get_current_price()


class CourseDetailSerializer(CourseSerializer):
    """Extended serializer for detailed course view with chapters and episodes"""
    chapters = serializers.SerializerMethodField()
    
    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ['chapters']
        
    def get_chapters(self, obj):
        chapters = Chapter.objects.filter(
            episodes__course=obj
        ).distinct().order_by('number')
        
        result = []
        for chapter in chapters:
            chapter_data = ChapterSerializer(chapter).data
            episodes = Episode.objects.filter(
                course=obj, chapter=chapter
            ).order_by('order')
            chapter_data['episodes'] = EpisodeSerializer(episodes, many=True).data
            result.append(chapter_data)
            
        return result

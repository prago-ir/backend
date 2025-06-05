from rest_framework import serializers
from .models import Post
from accounts.serializers import AuthorSerializer  # Assuming you have this
# Assuming you have these
from taxonomy.serializers import CategorySerializer, TagSerializer


class PostListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    featured_image_url = serializers.SerializerMethodField()
    # Assuming author has a 'user' field which has 'first_name' and 'last_name' or 'username'
    author_name = serializers.CharField(
        source='author.user.get_full_name', read_only=True, default=None)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'excerpt', 'featured_image_url',
            'author', 'author_name', 'categories', 'tags', 'published_at',
            'views_count', 'likes_count', 'average_read_time', 'status'
        ]
        # Add 'status' if you want to show it in the list, useful for admin or previews

    def get_featured_image_url(self, obj):
        return obj.featured_image.url


class PostDetailSerializer(serializers.ModelSerializer):
    # Or a more detailed AuthorSerializer
    author = AuthorSerializer(read_only=True)
    categories = CategorySerializer(
        many=True, read_only=True)  # Or full CategorySerializer
    tags = TagSerializer(many=True, read_only=True)  # Or full TagSerializer
    featured_image_url = serializers.SerializerMethodField()
    author_name = serializers.CharField(
        source='author.user.get_full_name', read_only=True, default=None)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt', 'featured_image_url',
            'author', 'author_name', 'categories', 'tags', 'published_at', 'created_at', 'updated_at',
            'views_count', 'likes_count', 'average_read_time', 'status'
        ]

    def get_featured_image_url(self, obj):
        return obj.get_featured_image_url()

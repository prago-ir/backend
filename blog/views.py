from django.shortcuts import render
from django.utils import timezone
from django.db.models import F, Q, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny

from .models import Post, Category, Tag, Author
from .serializers import PostListSerializer, PostDetailSerializer
from taxonomy.serializers import CategorySerializer, TagSerializer  # For metadata
# from accounts.serializers import AuthorLiteSerializer


class PostListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # --- Fetch Pinned Posts ---
        pinned_posts_queryset = Post.objects.filter(
            is_pinned=True,
            status='published',
            published_at__lte=timezone.now()
            # Limit pinned posts, e.g., to 5
        ).select_related('author__user').prefetch_related('categories', 'tags').order_by('-published_at')[:5]

        pinned_posts_serializer = PostListSerializer(
            pinned_posts_queryset, many=True, context={'request': request})
        pinned_post_ids = [post.id for post in pinned_posts_queryset]
        # --- End Fetch Pinned Posts ---

        # --- Fetch Regular Posts (excluding pinned ones already fetched) ---
        queryset = Post.objects.filter(
            status='published',
            published_at__lte=timezone.now()
        ).select_related('author__user').prefetch_related('categories', 'tags')
        # --- End Fetch Regular Posts ---

        # Filtering (applies to the non-pinned posts)
        category_slug = request.query_params.get('category')
        tag_slug = request.query_params.get('tag')
        author_id = request.query_params.get('author')

        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        if author_id:
            queryset = queryset.filter(author__id=author_id)

        # Sorting (applies to the non-pinned posts)
        ordering = request.query_params.get('ordering', '-published_at')
        valid_ordering_fields = ['published_at',
                                 '-published_at', 'views_count', '-views_count']
        if ordering in valid_ordering_fields:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-published_at')

        # Pagination would typically apply to the 'queryset' of non-pinned posts
        # For simplicity, if you implement pagination, apply it here before serializing 'queryset'

        posts_serializer = PostListSerializer(
            queryset, many=True, context={'request': request})

        # Metadata for filters (consider if this should include data from pinned posts or only filterable posts)
        # For now, metadata is based on all published posts for broader filter options.
        all_published_post_ids = Post.objects.filter(
            status='published', published_at__lte=timezone.now()).values_list('id', flat=True)

        active_categories = Category.objects.filter(
            blog_posts__id__in=all_published_post_ids).distinct()
        active_tags = Tag.objects.filter(
            blog_posts__id__in=all_published_post_ids).distinct()

        metadata = {
            'categories': CategorySerializer(active_categories, many=True).data,
            'tags': TagSerializer(active_tags, many=True).data,
            'sort_options': [
                {'value': '-published_at', 'label': 'جدیدترین'},
                {'value': 'published_at', 'label': 'قدیمی‌ترین'},
                {'value': '-views_count', 'label': 'پربازدیدترین'},
            ]
        }

        return Response({
            'pinned_posts': pinned_posts_serializer.data,  # Add pinned posts here
            'posts': posts_serializer.data,
            'metadata': metadata
        }, status=status.HTTP_200_OK)


class PostDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            post = Post.objects.select_related('author__user').prefetch_related('categories', 'tags').get(
                slug=slug,
                status='published',
                published_at__lte=timezone.now()
            )
        except Post.DoesNotExist:
            return Response({"detail": "پست مورد نظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        post.views_count = F('views_count') + 1
        post.save(update_fields=['views_count'])
        post.refresh_from_db()

        serializer = PostDetailSerializer(post, context={'request': request})

        related_posts = []
        post_tags_ids = post.tags.values_list('id', flat=True)
        post_categories_ids = post.categories.values_list('id', flat=True)

        if post_tags_ids or post_categories_ids:
            shared_tags_posts = Post.objects.filter(
                tags__in=post_tags_ids,
                status='published',
                published_at__lte=timezone.now()
            ).exclude(id=post.id).distinct()

            shared_categories_posts = Post.objects.filter(
                categories__in=post_categories_ids,
                status='published',
                published_at__lte=timezone.now()
            ).exclude(id=post.id).distinct()

            related_posts_queryset = (shared_tags_posts | shared_categories_posts).distinct(
            ).order_by('-published_at')[:3]
            related_posts_serializer = PostListSerializer(
                related_posts_queryset, many=True, context={'request': request})
            related_posts = related_posts_serializer.data

        response_data = serializer.data
        response_data['related_posts'] = related_posts

        return Response(response_data, status=status.HTTP_200_OK)

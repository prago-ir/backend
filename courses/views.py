from django.views import View
from rest_framework import status
from rest_framework.response import Response

from .models import Course
from rest_framework.views import APIView
from .serializers import CourseSerializer
from django.db.models import Count


class CategoryListView(View):
    def get(self, request):
        pass


class TagListView(View):
    def get(self, request):
        pass




class CourseListView(APIView):
    def get(self, request):
        queryset = Course.objects.all()

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
            queryset = queryset.filter(organizer__in=organizer)
        if category:
            queryset = queryset.filter(category__in=category)

        # Sorting
        sort_option = request.query_params.get('sort', 'newest')
        if sort_option == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_option == 'popular':
            queryset = queryset.annotate(enrollment_count=Count('enrollment')).order_by('-enrollment_count')
        elif sort_option == 'priceLow':
            queryset = queryset.order_by('price')
        elif sort_option == 'priceHigh':
            queryset = queryset.order_by('-price')
        elif sort_option == 'ratingHigh':
            queryset = queryset.order_by('-rating')

        serializer = CourseSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
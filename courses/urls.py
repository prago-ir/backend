from django.urls import path
from .views import (
    CourseListView, CourseDetailView, LatestCoursesView, LatestRoadmapView,
    OwnedCoursesView, DashboardCourseDetailView,
    CourseEnrollmentView, UpdateProgressView, PopularCoursesView,
    RoadmapDetailView  # Add this import
)

urlpatterns = [
    # Public endpoints
    path('etc/latest-courses/', LatestCoursesView.as_view(), name='home-courses'),
    path('etc/popular-courses/', PopularCoursesView.as_view(),
         name='popular-courses'),
    path('etc/latest-roadmaps/', LatestRoadmapView.as_view(), name='latest-roadmaps'),
    # Consider renaming if it's combined content
    path('', CourseListView.as_view(), name='course-list'),
    path('roadmaps/<slug:slug>/', RoadmapDetailView.as_view(),
         name='roadmap-detail'),  # New URL
    path('my-courses/', OwnedCoursesView.as_view(), name='owned-courses'),
    # This should be specific to courses
    path('<slug:slug>/', CourseDetailView.as_view(), name='course-detail'),

    path('dashboard/courses/<slug:slug>/',
         DashboardCourseDetailView.as_view(), name='dashboard-course-detail'),
    path('<slug:slug>/enroll/',  # This is for courses
         CourseEnrollmentView.as_view(), name='course-enroll'),
    path('episodes/<int:episode_id>/progress/',
         UpdateProgressView.as_view(), name='update-progress'),
]

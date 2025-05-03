from django.urls import path
from .views import (
    CourseListView, CourseDetailView, LatestCoursesView, LatestRoadmapView,
    OwnedCoursesView, DashboardCourseDetailView,
    CourseEnrollmentView, UpdateProgressView, PopularCoursesView
)

urlpatterns = [
    # Public endpoints
    path('etc/latest-courses/', LatestCoursesView.as_view(), name='home-courses'),
    path('etc/popular-courses/', PopularCoursesView.as_view(),
         name='popular-courses'),
    path('etc/latest-roadmaps/', LatestRoadmapView.as_view(), name='latest-roadmaps'),
    path('', CourseListView.as_view(), name='course-list'),
    path('<slug:slug>/', CourseDetailView.as_view(), name='course-detail'),

    # Authenticated user endpoints
    path('my-courses/', OwnedCoursesView.as_view(), name='owned-courses'),
    path('dashboard/courses/<slug:slug>/',
         DashboardCourseDetailView.as_view(), name='dashboard-course-detail'),
    path('courses/<slug:slug>/enroll/',
         CourseEnrollmentView.as_view(), name='course-enroll'),
    path('episodes/<int:episode_id>/progress/',
         UpdateProgressView.as_view(), name='update-progress'),
]

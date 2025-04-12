from django.urls import path
from .views import (
    CourseListView, CourseDetailView, LatestCoursesView,
    OwnedCoursesView, DashboardCourseDetailView, 
    CourseEnrollmentView, UpdateProgressView
)

urlpatterns = [
    # Public endpoints
    path('latest-courses/', LatestCoursesView.as_view(), name='home-courses'),
    path('courses/', CourseListView.as_view(), name='course-list'),
    path('courses/<slug:slug>/', CourseDetailView.as_view(), name='course-detail'),
    
    # Authenticated user endpoints
    path('my-courses/', OwnedCoursesView.as_view(), name='owned-courses'),
    path('dashboard/courses/<slug:slug>/', DashboardCourseDetailView.as_view(), name='dashboard-course-detail'),
    path('courses/<slug:slug>/enroll/', CourseEnrollmentView.as_view(), name='course-enroll'),
    path('episodes/<int:episode_id>/progress/', UpdateProgressView.as_view(), name='update-progress'),
]

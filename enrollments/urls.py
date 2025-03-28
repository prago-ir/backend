from django.urls import path
from . import views

app_name = 'enrollments'

urlpatterns = [
    # Enrollment endpoints
    path('my-courses/', views.EnrollmentListView.as_view(), name='enrollment_list'),
    path('my-courses/<slug:course_slug>/', views.EnrollmentDetailView.as_view(), name='enrollment_detail'),
]

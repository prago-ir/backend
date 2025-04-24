from django.urls import path
from . import views

urlpatterns = [
    path('request-otp/', views.RequestOTPView.as_view(), name='request_otp_view'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify_otp_view'),
    path('complete-signup/', views.CompleteSignupView.as_view(), name='complete_signup_view'),
    path('auth/google/', views.GoogleAuthView.as_view(), name='google-auth'),  # Add this route
    path('check-username/', views.CheckUsername.as_view(), name='check_username'),
    path('login-via-password/', views.LoginViaPassword.as_view(), name='login_via_password'),
    path('user/', views.UserInfoView.as_view(), name='user-info'),  # Add this line
    path('logout/', views.LogoutView.as_view(), name='logout_view'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='change_password'),
]
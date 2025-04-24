import pyotp
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken


from .models import OTP, MyUser
from .serializers import MyUserSerializer
from .tasks import send_otp_email, send_otp_sms


# Add this new API view to your existing views.py file

class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Return the authenticated user's information.
        This endpoint requires the user to be authenticated via session or token.
        """
        # Serialize the current user's data
        serializer = MyUserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RequestOTPView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        identifier = request.data.get('identifier')
        email, phone = None, None

        if "@" in identifier:
            # Send Email
            email = identifier
        elif identifier.isdigit() or identifier.startswith("+"):
            # Send SMS
            phone = identifier

        if not email and not phone:
            return Response({"error": "Email or phone number is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate or retrieve the secret
        otp_record, created = OTP.objects.get_or_create(
            email=email,
            phone=phone,
            defaults={"secret": pyotp.random_base32()}
        )

        totp = pyotp.TOTP(otp_record.secret)
        otp = totp.now()  # Generate a time-based OTP
        
        # Send OTP asynchronously using Celery
        # if email:
        #     try:
        #         from django.core.mail import send_mail
        #         from django.conf import settings
                
        #         subject = "کد تایید پراگو"
        #         message = f"کد تایید ورود: {otp}"
        #         html_message = f"""
        #         <div style="font-family: Vazirmatn, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 5px;" dir="rtl">
        #             <h2 style="color: #333;">کد تایید پراگو</h2>
        #             <p>از این کد جهت احراز هویت خود استفاده کنید: {otp}</p>
        #         </div>
        #         """
        #         # Log all email settings for debugging
        #         print(f"Email settings: HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}, USER={settings.EMAIL_HOST_USER}")
                
        #         # Send immediately for debugging
        #         result = send_mail(
        #             subject=subject,
        #             message=message,
        #             from_email=settings.DEFAULT_FROM_EMAIL,
        #             recipient_list=[email],
        #             html_message=html_message,
        #             fail_silently=False
        #         )
        #         print(f"Direct email send result: {result}")
                
        #         # Also try the async version
        #         send_otp_email.delay(email, otp)
        #     except Exception as e:
        #         print(f"Email send error: {str(e)}")
        #         # Still try the async version
        #         send_otp_email.delay(email, otp)
        # elif phone:
        #     send_otp_sms.delay(phone, otp)
        print(f"otp for {identifier} is {otp}")

        return Response({"message": "OTP sent successfully", "otp": otp}, status=status.HTTP_200_OK)



class VerifyOTPView(APIView):
    # permission_classes = [IsAuthenticated]
    
    def post(self, request):
        otp = request.data.get('otp')
        identifier = request.data.get('identifier')
        email, phone = None, None
        
        if "@" in identifier:
            # Send Email
            email = identifier
        elif identifier.isdigit() or identifier.startswith("+"):
            # Send SMS
            phone = identifier

        try:
            otp_record = OTP.objects.get(email=email, phone=phone)
            totp = pyotp.TOTP(otp_record.secret)

            if totp.verify(otp):
                # Check if the user exists
                user = MyUser.objects.filter(email=email).first() or MyUser.objects.filter(phone=phone).first()
                if user:
                    # Authenticate the user
                    user = authenticate(email=email, phone=phone)
                    login(request, user)

                    return Response({"message": "Login successful.", "user_id": user.id}, status=status.HTTP_200_OK)
                else:
                    # No existing user, they need to sign up
                    return Response({
                        "message": "OTP verified. Proceed to signup.",
                        "needs_signup": True  # Add this flag
                    }, status=status.HTTP_200_OK)
            else:
                return Response({"error": f"Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        except OTP.DoesNotExist:
            return Response({"error": "OTP record not found."}, status=status.HTTP_400_BAD_REQUEST)


class CompleteSignupView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = MyUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "Signup complete.", "user_id": user.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class LoginViaPassword(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        email = request.data.get('email')
        phone = request.data.get('phone')
        password = request.data.get('password')
        username = request.data.get('username')

        user = authenticate(username=username, email=email, phone=phone, password=password)
        if user:
            login(request, user)
            return Response({"message": "Login successful.", "user_id": user.id}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)


class CheckUsername(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        username = request.query_params.get('username')
        user = MyUser.objects.filter(username=username).first()
        if user:
            return Response({"error": "Username not available."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Username available."}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.logout()
        return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)
    


class RequestResetPassword(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            token = PasswordResetTokenGenerator().make_token(user)
            
            # Send token asynchronously via Celery
            subject = "Password Reset Request"
            message = f"Use this token to reset your password: {token}"
            html_message = f"""
            <div style="font-family: Vazirmatn, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee;" dir="rtl">
                <h2>درخواست ریست پسورد پراگو</h2>
                <p>ما درخواستی برای ریست پسورد شما دریافت کردیم. از لینک زیر استفاده کنید:</p>
                <div style="background-color: #f4f4f4; padding: 10px; margin: 15px 0; text-align: left;">
                    <a href="https://prago.ir/reset-password/{token}">https://prago.ir/reset-password/{token}</a>
                </div>
                <p>اگر شما درخواست ریست پسورد نداده اید، لطفا این ایمیل را نادیده بگیرید.</p>
                <p>پراگو | هر آنچه برای گذر نیاز دارید</p>
            </div>
            """
            from .tasks import send_email_task
            send_email_task.delay(subject, message, [user.email], html_message)
            
            return Response({"message": "Password reset token sent."}, status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        


class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        identifier = request.data.get("identifier")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        try:
            user = MyUser.objects.get(email=identifier) if "@" in identifier else MyUser.objects.get(phone=identifier)
            
            # Validate token
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise ValidationError("Invalid or expired token.")
            
            # Update password
            user.set_password(new_password)
            user.save()
            
            return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
        except MyUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
        

class GoogleAuthView(APIView):
    """
    Handle Google OAuth authentication data from frontend
    """
    def post(self, request):
        data = request.data
        email = data.get('email')
        sub = data.get('sub')  # Google's unique identifier
        
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if a user with this email already exists
        user = MyUser .objects.filter(email=email).first()
        needs_profile = False
        
        # If user doesn't exist, create a new one with Google data
        if not user:
            try:
                # Create a new user
                user = MyUser.objects.create(
                    email=email,
                    username=f"google_{sub[-8:]}",  # Create a username based on Google ID
                    is_active=True
                )
                
                # Set user fields if provided
                if data.get('name'):
                    # Split name if given and family names aren't provided
                    if not data.get('given_name') and ' ' in data.get('name'):
                        first_name, last_name = data.get('name').rsplit(' ', 1)
                        user.first_name = first_name
                        user.last_name = last_name
                    else:
                        user.first_name = data.get('given_name', '')
                        user.last_name = data.get('family_name', '')
                
                # Save user data
                user.save()
                
                # Flag that user needs to complete profile (add phone, etc.)
                needs_profile = True
                
            except Exception as e:
                return Response(
                    {"error": f"Failed to create user: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Generate tokens for the user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "Google authentication successful",
            "user_id": user.id,
            "needs_profile": needs_profile,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }, status=status.HTTP_200_OK)
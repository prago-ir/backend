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


class RequestOTPView(APIView):
    permission_classes = [IsAuthenticated]

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

        # Send OTP logic here (SMS or Email)
        print(otp)

        return Response({"message": "OTP sent.", "otp": otp}, status=status.HTTP_200_OK)



class VerifyOTPView(APIView):
    permission_classes = [IsAuthenticated]
    
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
                    return Response({"message": "OTP verified. Proceed to signup."}, status=status.HTTP_200_OK)
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
        identifier = request.data.get("identifier")
        try:
            user = MyUser.objects.get(email=identifier) if "@" in identifier else MyUser.objects.get(phone=identifier)
            token = PasswordResetTokenGenerator().make_token(user)
            
            # Send token via email or SMS
            if "@" in identifier:
                # Email sending logic here
                pass
            else:
                # Implement SMS sending logic here
                pass
            
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
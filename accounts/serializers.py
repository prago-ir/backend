from rest_framework import serializers
from .models import MyUser, OTP

class MyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['id', 'email', 'phone', 'username', 'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        if not attrs.get('phone'):
            raise serializers.ValidationError({"phone": "Phone number is required."})
        return attrs

    def create(self, validated_data):
        return MyUser.objects.create_user(**validated_data)

class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = ['email', 'phone', 'otp']

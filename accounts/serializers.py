from rest_framework import serializers
from .models import MyUser, OTP, Organizer, Teacher


class MyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['id', 'email', 'phone', 'username',
                  'first_name', 'last_name', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        if not attrs.get('phone') and not attrs.get('email'):
            raise serializers.ValidationError(
                {"Phone number or email is required."})
        return attrs

    def create(self, validated_data):
        return MyUser.objects.create_user(**validated_data)


class OTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTP
        fields = ['email', 'phone', 'otp']


class OrganizerSerializer(serializers.ModelSerializer):
    organization_logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Organizer
        fields = ['id', 'organization_name',
                  # Changed organization_logo to organization_logo_url
                  'organization_logo_url', 'organization_description']

    def get_organization_logo_url(self, obj):
        if obj.organization_logo:
            # This will be the relative path starting with MEDIA_URL
            return obj.organization_logo.url
        return None


class TeacherSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Teacher
        fields = ['id', 'full_name', 'avatar_url',  # Changed avatar to avatar_url
                  'biography', 'number_of_courses']

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url  # This will be the relative path starting with MEDIA_URL
        return None

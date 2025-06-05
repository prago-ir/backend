from rest_framework import serializers
from .models import MyUser, OTP, Organizer, Author, Teacher, Profile


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


class AuthorSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = ['id', 'full_name', 'avatar_url',
                  'biography', 'number_of_posts']

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url  # This will be the relative path starting with MEDIA_URL
        return None


class UserProfileSerializer(serializers.ModelSerializer):
    # Fields from MyUser model
    email = serializers.EmailField(
        required=False, allow_blank=True, allow_null=True)
    phone = serializers.CharField(
        required=False, allow_blank=True, allow_null=True)
    username = serializers.CharField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    # Field from Profile model
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = MyUser
        fields = ['id', 'email', 'phone', 'username',
                  'first_name', 'last_name', 'avatar']
        read_only_fields = ['id']

    def validate_username(self, value):
        # Ensure username is unique if it's being changed
        user = self.context['request'].user
        if MyUser.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError(
                "این نام کاربری قبلا استفاده شده است.")
        return value

    def validate_email(self, value):
        # Ensure email is unique if it's being changed and not empty
        user = self.context['request'].user
        if value and MyUser.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError(
                "این ایمیل قبلا استفاده شده است.")
        return value

    def validate_phone(self, value):
        # Ensure phone is unique if it's being changed and not empty
        user = self.context['request'].user
        if value and MyUser.objects.exclude(pk=user.pk).filter(phone=value).exists():
            raise serializers.ValidationError(
                "این شماره تماس قبلا استفاده شده است.")
        return value

    def get_avatar(self, obj):
        profile = Profile.objects.get(user=obj)
        request = self.context.get('request')
        if profile.avatar and hasattr(profile.avatar, 'url'):
            if request is not None:
                return request.build_absolute_uri(profile.avatar.url)
            return profile.avatar.url
        return None

    def to_representation(self, instance):
        """Modify output representation to include avatar URL."""
        representation = super().to_representation(instance)
        profile, _ = Profile.objects.get_or_create(user=instance)
        request = self.context.get('request')
        if profile.avatar and hasattr(profile.avatar, 'url'):
            if request:
                representation['avatar'] = request.build_absolute_uri(
                    profile.avatar.url)
            else:
                representation['avatar'] = profile.avatar.url
        else:
            representation['avatar'] = None
        return representation

    def update(self, instance, validated_data):
        # Update MyUser fields
        instance.first_name = validated_data.get(
            'first_name', instance.first_name)
        instance.last_name = validated_data.get(
            'last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)

        # Handle email and phone carefully, allowing them to be null/blank
        new_email = validated_data.get('email', instance.email)
        instance.email = new_email if new_email is not None else instance.email

        new_phone = validated_data.get('phone', instance.phone)
        instance.phone = new_phone if new_phone is not None else instance.phone

        instance.save()

        # Update Profile fields (avatar)
        profile, _ = Profile.objects.get_or_create(user=instance)
        if 'avatar' in validated_data:
            # If avatar is explicitly set to null (e.g. to remove it)
            if validated_data['avatar'] is None:
                profile.avatar.delete(save=True)
            else:
                profile.avatar = validated_data.get('avatar', profile.avatar)
        profile.save()

        return instance

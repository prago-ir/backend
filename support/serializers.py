from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Ticket, TicketMessage, TicketMessageAttachment
# Ensure uuid is imported if not already

User = get_user_model()


class TicketMessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessageAttachment
        fields = ['id', 'file', 'file_url', 'content_type', 'uploaded_at']
        read_only_fields = ['file_url', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class SenderDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for sender details (name and avatar).
    Assumes User model has a related 'profile' and Profile has 'avatar'.
    """
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = User  # Or your specific User model if not using default
        fields = ['name', 'image']

    def get_name(self, user_obj):
        # Prioritize full name, fall back to username
        if hasattr(user_obj, 'get_full_name') and user_obj.get_full_name():
            return user_obj.get_full_name()
        return user_obj.username

    def get_image(self, user_obj):
        request = self.context.get('request')
        # Attempt to get profile and avatar
        # This assumes a OneToOneField named 'profile' from User to Profile model
        # and an ImageField named 'avatar' on the Profile model.
        try:
            if hasattr(user_obj, 'profile') and user_obj.profile.avatar:
                if request:
                    return request.build_absolute_uri(user_obj.profile.avatar.url)
                return user_obj.profile.avatar.url
        except AttributeError:  # Handles if 'profile' or 'profile.avatar' doesn't exist
            pass
        return None


class TicketMessageSerializer(serializers.ModelSerializer):
    attachments = TicketMessageAttachmentSerializer(many=True, read_only=True)
    # sender field will now be an object with name and image
    sender_details = SenderDetailSerializer(source='sender', read_only=True)
    is_staff = serializers.SerializerMethodField()  # Changed from direct field

    class Meta:
        model = TicketMessage
        fields = [
            'id',
            'ticket',
            'sender',  # Keep sender ID for writing/creating messages
            'sender_details',  # Add this for detailed sender info on read
            'message',
            'created_at',
            'attachments',
            'is_staff'  # Now a SerializerMethodField
        ]
        read_only_fields = ['created_at', 'sender_details',
                            'is_staff']  # is_staff is read_only
        extra_kwargs = {
            # Ticket ID is enough for creating a message
            'ticket': {'write_only': True},
            # Sender ID is enough for creating a message
            'sender': {'write_only': True}
        }

    def get_is_staff(self, obj):
        # obj is an instance of TicketMessage
        # Check if the sender of the message is a staff member
        if obj.sender:
            return obj.sender.is_staff
        return False  # Default if sender is somehow None

    def create(self, validated_data):
        # 'sender' in validated_data will be the user instance passed from the view
        return super().create(validated_data)


class TicketSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    department_display = serializers.CharField(
        source='get_department_display', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_number', 'user', 'subject',
            'status', 'status_display', 'department', 'department_display',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id',  # Typically, id is read-only after creation
            'user',
            'created_at',
            'updated_at',
            'status_display',
            'department_display'
        ]
        # Ensure 'ticket_number' is not listed as read_only here.
        # 'status' and 'department' are correctly writable.


class TicketDetailSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    # This will now use the updated TicketMessageSerializer
    messages = TicketMessageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)
    department_display = serializers.CharField(
        source='get_department_display', read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id', 'ticket_number', 'user', 'subject',
            'status', 'status_display', 'department', 'department_display',
            'created_at', 'updated_at', 'messages'
        ]

    # If you need to pass context (like the request for absolute URIs) to nested serializers:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure context is passed to nested serializers if needed for URL building
        if 'context' in kwargs:
            self.fields['messages'].context.update(kwargs['context'])

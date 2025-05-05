from rest_framework import serializers
from .models import Ticket, TicketMessage, TicketMessageAttachment


class TicketMessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TicketMessageAttachment
        fields = ['id', 'file_name', 'file_size',
                  'content_type', 'uploaded_at', 'file_url']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    is_staff = serializers.SerializerMethodField()
    attachments = TicketMessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'sender', 'sender_name', 'is_staff',
                  'message', 'created_at', 'attachments']

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username

    def get_is_staff(self, obj):
        return obj.sender.is_staff


class TicketSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'ticket_number', 'subject', 'department', 'status',
                  'created_at', 'updated_at', 'message_count']

    def get_message_count(self, obj):
        return obj.messages.count()


class TicketDetailSerializer(serializers.ModelSerializer):
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'ticket_number', 'subject', 'department', 'status',
                  'created_at', 'updated_at', 'messages']

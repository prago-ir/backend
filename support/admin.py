from django.contrib import admin
from django.utils.html import format_html
from .models import Ticket, TicketMessage, TicketMessageAttachment


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ['created_at']
    fields = ['sender', 'message', 'created_at']
    show_change_link = True


class TicketMessageAttachmentInline(admin.TabularInline):
    model = TicketMessageAttachment
    extra = 0
    readonly_fields = ['file_name', 'file_size',
                       'content_type', 'uploaded_at', 'file_preview']
    fields = ['file', 'file_name', 'file_size',
              'content_type', 'uploaded_at', 'file_preview']

    def file_preview(self, obj):
        if obj.content_type.startswith('image/'):
            return format_html('<a href="{}" target="_blank"><img src="{}" width="100" /></a>', obj.file.url, obj.file.url)
        return format_html('<a href="{}" target="_blank">Download File</a>', obj.file.url)

    file_preview.short_description = 'Preview'


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_number', 'subject', 'department',
                    'status', 'user', 'created_at', 'updated_at']
    list_filter = ['status', 'department', 'created_at', 'updated_at']
    search_fields = ['ticket_number', 'subject',
                     'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TicketMessageInline]
    date_hierarchy = 'created_at'

    fieldsets = [
        ('Ticket Information', {
            'fields': ('ticket_number', 'subject', 'user', 'department', 'status')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    ]


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'ticket_link', 'sender',
                    'short_message', 'created_at', 'has_attachments']
    list_filter = ['created_at', 'sender__is_staff']
    search_fields = ['message', 'ticket__ticket_number', 'sender__username']
    readonly_fields = ['created_at']
    inlines = [TicketMessageAttachmentInline]

    def ticket_link(self, obj):
        url = f'/admin/support/ticket/{obj.ticket.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.ticket.ticket_number)

    ticket_link.short_description = 'Ticket'

    def short_message(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message

    short_message.short_description = 'Message'

    def has_attachments(self, obj):
        return obj.attachments.exists()

    has_attachments.boolean = True
    has_attachments.short_description = 'Has Attachments'


@admin.register(TicketMessageAttachment)
class TicketMessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_name', 'file_size_display',
                    'content_type', 'message_link', 'uploaded_at']
    list_filter = ['content_type', 'uploaded_at']
    search_fields = ['file_name', 'message__ticket__ticket_number']
    readonly_fields = ['file_name', 'file_size',
                       'content_type', 'uploaded_at', 'file_preview']

    def file_size_display(self, obj):
        # Convert bytes to KB or MB for better readability
        if obj.file_size < 1024:
            return f"{obj.file_size} bytes"
        elif obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        else:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"

    file_size_display.short_description = 'File Size'

    def message_link(self, obj):
        url = f'/admin/support/ticketmessage/{obj.message.id}/change/'
        return format_html('<a href="{}">{}</a>', url, f"Message {obj.message.id}")

    message_link.short_description = 'Message'

    def file_preview(self, obj):
        if obj.content_type.startswith('image/'):
            return format_html('<a href="{}" target="_blank"><img src="{}" width="300" /></a>', obj.file.url, obj.file.url)
        return format_html('<a href="{}" target="_blank">Download File</a>', obj.file.url)

    file_preview.short_description = 'File Preview'

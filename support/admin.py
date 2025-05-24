from django.contrib import admin
from django.utils.html import format_html
from .models import Ticket, TicketMessage, TicketMessageAttachment
from .forms import TicketMessageAdminForm

ANSWERED_STATUS = 'answered'

# Factory function to create a form class with the request


def get_ticket_message_admin_form_with_request(request_obj):
    class FormWithRequest(TicketMessageAdminForm):
        def __init__(self, *args, **kwargs):
            # Pass the request to the superclass constructor
            super().__init__(*args, **kwargs, request=request_obj)
    return FormWithRequest


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ['created_at']
    fields = ['sender', 'message', 'created_at']
    show_change_link = True

    def get_formset(self, request, obj=None, **kwargs):
        # Dynamically create the form class with the request
        current_form = get_ticket_message_admin_form_with_request(request)
        return super().get_formset(request, obj, form=current_form, **kwargs)


class TicketMessageAttachmentInline(admin.TabularInline):
    model = TicketMessageAttachment
    extra = 0
    readonly_fields = ['file_name', 'file_size',
                       'content_type', 'uploaded_at', 'file_preview']
    fields = ['file', 'file_name', 'file_size',
              'content_type', 'uploaded_at', 'file_preview']

    def file_preview(self, obj):
        if obj.file and hasattr(obj.file, 'url'):
            if obj.content_type and obj.content_type.startswith('image/'):
                return format_html('<a href="{}" target="_blank"><img src="{}" width="100" /></a>', obj.file.url, obj.file.url)
            return format_html('<a href="{}" target="_blank">Download File</a>', obj.file.url)
        return "No file"
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

    fieldsets = [
        ('Ticket Information', {
            'fields': ('ticket_number', 'subject', 'user', 'department', 'status')
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    ]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        ticket_to_update = None
        staff_message_added_or_changed = False

        for instance in instances:
            if isinstance(instance, TicketMessage):
                if instance in formset.new_objects:
                    if not instance.sender_id:  # Check if sender is not already set
                        instance.sender = request.user

                if instance.sender and instance.sender.is_staff:
                    if instance in formset.new_objects or instance in formset.changed_objects:
                        staff_message_added_or_changed = True

        if staff_message_added_or_changed:
            ticket_to_update = form.instance

        formset.save()  # Save the inlines

        if ticket_to_update and ticket_to_update.status != ANSWERED_STATUS:
            if ticket_to_update.status not in ['closed', 'resolved']:
                ticket_to_update.status = ANSWERED_STATUS
                ticket_to_update.save()


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'ticket_link', 'sender',
                    'short_message', 'created_at', 'has_attachments']
    list_filter = ['created_at', 'sender__is_staff']
    search_fields = ['message', 'ticket__ticket_number', 'sender__username']
    readonly_fields = ['created_at']
    inlines = [TicketMessageAttachmentInline]

    def get_form(self, request, obj=None, **kwargs):
        # Dynamically create the form class with the request
        current_form = get_ticket_message_admin_form_with_request(request)
        defaults = {'form': current_form}
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

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

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.sender = request.user

        is_staff_message = obj.sender and obj.sender.is_staff
        super().save_model(request, obj, form, change)

        if is_staff_message:
            ticket = obj.ticket
            if ticket and ticket.status != ANSWERED_STATUS:
                if ticket.status not in ['closed', 'resolved']:
                    ticket.status = ANSWERED_STATUS
                    ticket.save()


@admin.register(TicketMessageAttachment)
class TicketMessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_name', 'file_size_display',
                    'content_type', 'message_link', 'uploaded_at']
    list_filter = ['content_type', 'uploaded_at']
    search_fields = ['file_name', 'message__ticket__ticket_number']
    readonly_fields = ['file_name', 'file_size',
                       'content_type', 'uploaded_at', 'file_preview']

    def file_size_display(self, obj):
        if obj.file_size is None:
            return "N/A"
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
        if obj.file and hasattr(obj.file, 'url'):
            if obj.content_type and obj.content_type.startswith('image/'):
                return format_html('<a href="{}" target="_blank"><img src="{}" width="100" /></a>', obj.file.url, obj.file.url)
            return format_html('<a href="{}" target="_blank">Download File</a>', obj.file.url)
        return "No file"
    file_preview.short_description = 'File Preview'

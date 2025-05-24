from django.db import models


class Ticket(models.Model):
    department_choices = [
        ('sales', 'Sales'),
        ('support', 'Support'),
        ('billing', 'Billing'),
        ('technical', 'Technical'),
    ]

    status_choices = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('answered', 'Answered'),
        ('closed', 'Closed'),
        ('resolved', 'Resolved'),
    ]

    user = models.ForeignKey(
        'accounts.MyUser', on_delete=models.CASCADE, verbose_name='کاربر')
    ticket_number = models.CharField(
        max_length=20, unique=True, verbose_name='شماره تیکت')
    subject = models.CharField(max_length=255, verbose_name='موضوع')
    department = models.CharField(
        max_length=100, choices=department_choices, verbose_name='دپارتمان')
    status = models.CharField(
        max_length=20, default='open', choices=status_choices, verbose_name='وضعیت')

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='تاریخ به‌روزرسانی')

    class Meta:
        verbose_name = 'تیکت'
        verbose_name_plural = 'تیکت‌ها'
        ordering = ['-created_at']

    def __str__(self):
        return f'Ticket {self.ticket_number} - {self.subject} ({self.status})'


class TicketMessage(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name='messages', verbose_name='تیکت')
    sender = models.ForeignKey(
        'accounts.MyUser', on_delete=models.CASCADE, verbose_name='فرستنده')
    message = models.TextField(verbose_name='پیام')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='تاریخ ارسال')

    class Meta:
        verbose_name = 'پیام تیکت'
        verbose_name_plural = 'پیام‌های تیکت'
        ordering = ['created_at']

    def __str__(self):
        return f'Message from {self.sender} in Ticket {self.ticket.ticket_number}'


def ticket_attachment_path(instance, filename):
    """Define path where ticket message attachments will be stored"""
    # Will save to: media/tickets/ticket_123/message_456/filename
    return f'tickets/ticket_{instance.message.ticket.ticket_number}/message_{instance.message.id}/{filename}'


class TicketMessageAttachment(models.Model):
    message = models.ForeignKey(
        TicketMessage, on_delete=models.CASCADE, related_name='attachments', verbose_name='پیام')
    file = models.FileField(
        upload_to=ticket_attachment_path, verbose_name='فایل')
    file_name = models.CharField(max_length=255, verbose_name='نام فایل')
    file_size = models.PositiveIntegerField(verbose_name='حجم فایل (بایت)')
    content_type = models.CharField(max_length=100, verbose_name='نوع فایل')
    uploaded_at = models.DateTimeField(
        auto_now_add=True, verbose_name='تاریخ آپلود')

    class Meta:
        verbose_name = 'پیوست پیام'
        verbose_name_plural = 'پیوست‌های پیام'

    def __str__(self):
        return f'Attachment {self.file_name} for message {self.message.id}'

    def save(self, *args, **kwargs):
        # If this is a new attachment, set the file name and size
        if not self.pk and self.file:
            self.file_name = self.file.name
            self.file_size = self.file.size
            # You might need to determine content type differently depending on your needs

        super().save(*args, **kwargs)

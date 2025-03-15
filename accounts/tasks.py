from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_email_task(subject, message, recipient_list, html_message=None):
    """
    Task to send email asynchronously
    """
    try:
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False
        )
        logger.info(f"Email sent to {recipient_list}: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {str(e)}")
        raise e

@shared_task
def send_sms_task(phone_number, message):
    """
    Task to send SMS asynchronously
    Uses your SMS provider's API
    """
    try:
        # Replace with your SMS service integration
        # Example with a hypothetical SMS service:
        # sms_service = SMSService(settings.SMS_API_KEY)
        # result = sms_service.send(phone_number, message)
        
        # For demonstration (replace with actual SMS sending):
        logger.info(f"SMS sent to {phone_number}: {message}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
        raise e

@shared_task
def send_otp_email(email, otp):
    """
    Task to send OTP via email
    """
    subject = "کد تایید پراگو"
    message = f"کد تایید ورود: {otp}"
    html_message = f"""
    <div style="font-family: Vazirmatn, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 5px;" dir="rtl">
        <h2 style="color: #333;">کد تایید پراگو</h2>
        <p>از این کد جهت احراز هویت خود استفاده کنید</p>
        <div style="background-color: #f4f4f4; padding: 10px; border-radius: 4px; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold;">
            {otp}
        </div>
        <p style="margin-top: 20px; font-size: 12px; color: #777;">
            این کد تا ده دقیقه دیگر اعتبار دارد. اگر شما این کد را درخواست نکرده اید، لطفا این ایمیل را نادیده بگیرید.
        </p>
        <p><a href="https://prago.ir">پراگو</a>| هر آنچه برای گذر نیاز دارید</p>
    </div>
    """
    return send_email_task(subject, message, [email], html_message)

@shared_task
def send_otp_sms(phone, otp):
    """
    Task to send OTP via SMS
    """
    message = f"کد تایید ورود: {otp}"
    return send_sms_task(phone, message)
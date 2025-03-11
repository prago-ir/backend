from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError

class MyUserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, username=None, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError("باید یا ایمیل یا شماره تماس وارد شود.")

        email = self.normalize_email(email) if email else None
        user = self.model(email=email, phone=phone, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email=email, username=username, password=password, **extra_fields)


PHONE_VALIDATOR = RegexValidator(
    r"^(?:\+98|0)9\d{9}$",
    "فرمت شماره وارد شده نادرست است"
)


class MyUser(AbstractUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True, verbose_name="ایمیل")
    phone = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        verbose_name="شماره تماس",
        validators=[PHONE_VALIDATOR],
        help_text="شماره تماس یا با فرمت: 09123456789, یا با فرمت: +989123456789 نوشته شود"
    )
    username = models.CharField(max_length=50, unique=True, verbose_name="نام کاربری")
    first_name = models.CharField(max_length=50, verbose_name="نام")
    last_name = models.CharField(max_length=50, verbose_name="نام خانوادگی")
    is_active = models.BooleanField(default=True, verbose_name="فعال است")
    is_staff = models.BooleanField(default=False, verbose_name="کارمند است")

    objects = MyUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.full_name()
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        if not self.email or not self.phone:
            raise ValidationError("باید یا ایمیل یا شماره تماس وارد شود.")
        return super().clean()
    
    def is_teacher(self):
        """Check if user is a teacher"""
        return self.groups.filter(name='Teachers').exists()
    
    def is_organizer(self):
        """Check if user is an organizer"""
        return self.groups.filter(name='Organizers').exists()
    
    def is_author(self):
        """Check if user is an author"""
        return self.groups.filter(name='Authors').exists()
    
    def get_roles(self):
        """Get all user roles"""
        roles = []
        if self.is_teacher():
            roles.append('teacher')
        if self.is_organizer():
            roles.append('organizer')
        if self.is_author():
            roles.append('author')
        if self.is_staff:
            roles.append('staff')
        if self.is_superuser:
            roles.append('admin')
        return roles


class OTP(models.Model):
    email = models.EmailField(null=True, blank=True, verbose_name="ایمیل")
    phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="شماره تماس",
        validators=[PHONE_VALIDATOR],
        help_text="شماره تماس یا با فرمت: 09123456789, یا با فرمت: +989123456789 نوشته شود"
    )
    secret = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        verbose_name ="رمز‌ یکبار مصرف"
        verbose_name_plural ="رمز‌های یکبار مصرف"

    def __str__(self):
        return self.email or self.phone


class Profile(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='تصویر پروفایل')
    bio = models.TextField(blank=True, verbose_name='بیوگرافی')
    website = models.URLField(blank=True, verbose_name='وب‌سایت')
    social_links = models.JSONField(default=dict, blank=True, verbose_name='شبکه‌های اجتماعی')
    # Basic common fields for all users
    birth_date = models.DateField(null=True, blank=True, verbose_name='تاریخ تولد')
    address = models.TextField(blank=True, verbose_name='آدرس')
    education = models.CharField(max_length=100, blank=True, verbose_name='تحصیلات')
    
    class Meta:
        verbose_name = 'پروفایل کاربر'
        verbose_name_plural = 'پروفایل‌های کاربران'
        
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"Profile for {self.full_name()}"
    
    
class Teacher(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='teacher_profile', null=True, blank=True)
    first_name = models.CharField(max_length=50, blank=True, verbose_name="نام مدرس")
    last_name = models.CharField(max_length=50, blank=True, verbose_name="نام خانوادگی مدرس")
    slug = models.SlugField(max_length=50, unique=True, verbose_name='اسلاگ مدرس')
    biography = models.TextField(blank=True, verbose_name='بیوگرافی مدرس')
    

    class Meta:
        verbose_name = 'پروفایل مدرس'
        verbose_name_plural = 'پروفایل‌های مدرسین'
        
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"Teacher: {self.full_name()}"


class Organizer(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='organizer_profile', null=True, blank=True)
    organization_name = models.CharField(max_length=255, verbose_name='نام سازمان')
    organization_slug = models.SlugField(max_length=255, unique=True, verbose_name='اسلاگ سازمان')
    organization_logo = models.ImageField(upload_to='organizer_logos/', blank=True, null=True, verbose_name='لوگو سازمان')
    organization_website = models.URLField(blank=True, verbose_name='وب‌سایت سازمان')
    organization_description = models.TextField(blank=True, verbose_name='درباره سازمان')
    contact_email = models.EmailField(blank=True, verbose_name='ایمیل تماس')
    contact_phone = models.CharField(max_length=15, blank=True, verbose_name='شماره تماس')
    verified = models.BooleanField(default=False, verbose_name='تایید شده')

    class Meta:
        verbose_name = 'پروفایل برگزارکننده'
        verbose_name_plural = 'پروفایل‌های برگزارکنندگان'
    
    def __str__(self):
        return f"Organizer: {self.organization_name}"


class Author(models.Model):
    user = models.OneToOneField(MyUser, on_delete=models.CASCADE, related_name='author_profile', null=True, blank=True)
    first_name = models.CharField(max_length=50, blank=True, verbose_name="نام مدرس")
    last_name = models.CharField(max_length=50, blank=True, verbose_name="نام خانوادگی مدرس")
    slug = models.SlugField(max_length=50, unique=True, verbose_name='اسلاگ مدرس')
    biography = models.TextField(blank=True, verbose_name='بیوگرافی')
    
    class Meta:
        verbose_name = 'پروفایل نویسنده'
        verbose_name_plural = 'پروفایل‌های نویسندگان'
        
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"Author: {self.user.full_name()}"
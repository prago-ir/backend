from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class MyUserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, username=None, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError("The user must have either an email or a phone number.")

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
    # r"^(\+?\d{0,4}|0)?\s?-?\s?(\(?\d{3}\)?)\s?-?\s?(\(?\d{3}\)?)\s?-?\s?(\(?\d{4}\)?)?$",
    r"^(?:\+98|0)9\d{9}$",
    "The phone number provided is invalid"
)


class MyUser(AbstractUser, PermissionsMixin):
    email = models.EmailField(unique=True, null=True, blank=True, verbose_name=_("Email"))
    phone = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Phone number"),
        validators=[PHONE_VALIDATOR],
        help_text=_("Either enter in this format: 09123456789, or this format: +989123456789")
    )
    username = models.CharField(max_length=50, unique=True, verbose_name=_("Username"))
    first_name = models.CharField(max_length=50, verbose_name=_("First name"))
    last_name = models.CharField(max_length=50, verbose_name=_("Last name"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    is_staff = models.BooleanField(default=False, verbose_name=_("Is staff"))

    objects = MyUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username or self.email or self.phone

    def clean(self):
        if not self.email or not self.phone:
            raise ValidationError(_("At least one of email or phone number must be provided."))
        return super().clean()


class OTP(models.Model):
    email = models.EmailField(null=True, blank=True, verbose_name=_("Email"))
    phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name=_("Phone number"),
        validators=[PHONE_VALIDATOR],
        help_text=_("Either enter in this format: 09123456789, or this format: +989123456789")
    )
    secret = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        verbose_name = _("رمز‌ یکبار مصرف")
        verbose_name_plural = _("رمز‌های یکبار مصرف")

    def __str__(self):
        return self.email or self.phone

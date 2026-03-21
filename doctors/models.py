from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models


class Doctor(models.Model):
    """Doctor model with specialization and availability"""

    phone_validator = RegexValidator(
        regex=r'^\+?\d{9,15}Ksh',
        message='Enter a valid phone number'
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_profile'
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    specialization = models.CharField(max_length=100)

    license_number = models.CharField(
        max_length=50,
        unique=True
    )

    contact = models.CharField(
        max_length=20,
        validators=[phone_validator]
    )

    email = models.EmailField(blank=True, null=True)

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    availability = models.TextField(
        blank=True,
        null=True,
        help_text="Example: Monday–Friday 9AM–5PM"
    )

    bio = models.TextField(blank=True, null=True)

    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} ({self.specialization})"

    class Meta:
        db_table = "doctors_doctor"
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
        ordering = ["specialization", "last_name"]
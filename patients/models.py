from datetime import date

from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models


class Patient(models.Model):
    """Patient model with comprehensive health information"""

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    BLOOD_TYPE_CHOICES = [
        ('O+', 'O+'), ('O-', 'O-'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient_profile'
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()

    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES
    )

    contact = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?\d{9,15}$',
                message='Enter a valid phone number'
            )
        ]
    )

    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    county = models.CharField(max_length=100, blank=True, null=True)

    blood_type = models.CharField(
        max_length=5,
        choices=BLOOD_TYPE_CHOICES,
        blank=True,
        null=True
    )

    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)

    medical_history = models.TextField(blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) <
            (self.date_of_birth.month, self.date_of_birth.day)
        )

    class Meta:
        db_table = "patients_patient"
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["-created_at"]


class VisitHistory(models.Model):
    """Medical visit history and records"""

    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name='visit_record'
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name='visit_history'
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name='visit_history'
    )

    visit_date = models.DateTimeField(auto_now_add=True)

    diagnosis = models.TextField(blank=True, null=True)
    treatment = models.TextField(blank=True, null=True)
    prescription = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Visit: {self.patient} - Dr. {self.doctor} ({self.visit_date.date()})"

    class Meta:
        db_table = "patients_visit_history"
        verbose_name = "Visit History"
        verbose_name_plural = "Visit Histories"
        ordering = ["-visit_date"]
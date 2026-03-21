from django.contrib.auth.models import User
from django.db import models


class Appointment(models.Model):
    """Appointment model for scheduling and tracking"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('referred', 'Referred'),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    reason = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_appointments"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient} - Dr. {self.doctor} ({self.appointment_date} {self.appointment_time})"

    class Meta:
        db_table = "appointments_appointment"
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["-appointment_date", "-appointment_time"]
        unique_together = ["patient", "doctor", "appointment_date", "appointment_time"]


class Referral(models.Model):
    """Tracks patient referrals from one doctor to another"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
    ]

    original_appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='referral'
    )

    referred_from = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name='referrals_made'
    )

    referred_to = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name='referrals_received'
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name='referrals'
    )

    reason = models.TextField()

    new_appointment = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_from_appointment'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (f"Referral: {self.patient} from Dr. {self.referred_from} "
                f"to Dr. {self.referred_to}")

    class Meta:
        db_table = "appointments_referral"
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"
        ordering = ["-created_at"]
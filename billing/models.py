from django.db import models


class Bill(models.Model):
    """Main bill linked to an appointment"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent to Patient'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    appointment = models.OneToOneField(
        "appointments.Appointment",
        on_delete=models.CASCADE,
        related_name='bill'
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name='bills'
    )

    doctor = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.CASCADE,
        related_name='bills'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Discount amount in dollars"
    )

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Bill #{self.id} — {self.patient} ({self.status})"

    @property
    def subtotal(self):
        return sum(item.total for item in self.items.all())

    @property
    def total(self):
        return max(self.subtotal - self.discount, 0)

    class Meta:
        db_table = "billing_bill"
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        ordering = ["-created_at"]


class BillItem(models.Model):
    """Individual line items on a bill"""

    CATEGORY_CHOICES = [
        ('consultation', 'Consultation Fee'),
        ('lab', 'Lab Test'),
        ('medication', 'Medication'),
        ('procedure', 'Procedure'),
        ('other', 'Other'),
    ]

    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name='items'
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='consultation'
    )

    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} x{self.quantity} = ${self.total}"

    @property
    def total(self):
        return self.quantity * self.unit_price

    class Meta:
        db_table = "billing_bill_item"
        verbose_name = "Bill Item"
        verbose_name_plural = "Bill Items"


class Payment(models.Model):
    """Payment record for a bill"""

    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('insurance', 'Insurance'),
        ('other', 'Other'),
    ]

    bill = models.OneToOneField(
        Bill,
        on_delete=models.CASCADE,
        related_name='payment'
    )

    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='mpesa'
    )
    mpesa_number = models.CharField(
        max_length=20,
        blank=True, null=True,
        help_text="e.g. 0712345678"
    )
    transaction_code = models.CharField(
        max_length=50,
        blank=True, null=True,
        help_text="M-Pesa transaction code e.g. QKA1234XYZ"
    )
    notes = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments_recorded'
    )
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for Bill #{self.bill.id} — {self.amount_paid} via {self.get_payment_method_display()}"

    class Meta:
        db_table = "billing_payment"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
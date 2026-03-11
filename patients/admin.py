from django.contrib import admin

# Register your models here.
from django.contrib import admin
from patients.models import Patient, VisitHistory

admin.site.register(Patient)
admin.site.register(VisitHistory)
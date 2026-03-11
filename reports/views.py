from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


from core.views import check_role
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment



@login_required
@check_role('admin')
def dashboard_report(request):
    """Admin dashboard report"""
    context = {
        'total_patients': Patient.objects.count(),
        'total_doctors': Doctor.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'pending_appointments': Appointment.objects.filter(status='pending').count(),
        'completed_appointments': Appointment.objects.filter(status='completed').count(),
        'cancelled_appointments': Appointment.objects.filter(status='cancelled').count(),
    }

    today = timezone.now().date()
    context['todays_appointments'] = Appointment.objects.filter(
        appointment_date=today
    ).select_related('patient', 'doctor')
    total = Appointment.objects.count()
    completed = Appointment.objects.filter(status='completed').count()
    context['completion_rate'] = round((completed / total * 100), 1) if total > 0 else 0

    return render(request, 'reports/dashboard_report.html', context)


@login_required
@check_role('admin')
def appointment_report(request):
    """Appointment statistics report"""
    appointments = Appointment.objects.all()

    context = {
        'total_appointments': appointments.count(),
        'pending': appointments.filter(status='pending').count(),
        'completed': appointments.filter(status='completed').count(),
        'cancelled': appointments.filter(status='cancelled').count(),
        'appointments': appointments.order_by('-appointment_date')[:50],
    }
    return render(request, 'reports/appointment_report.html', context)


@login_required
@check_role('admin')
def patient_report(request):
    """Patient statistics report"""
    patients = Patient.objects.all()
    context = {
        'total_patients': patients.count(),
        'patients': patients,
    }
    return render(request, 'reports/patient_report.html', context)




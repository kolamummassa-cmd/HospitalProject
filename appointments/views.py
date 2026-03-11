from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Appointment
from patients.models import Patient
from doctors.models import Doctor

from core.views import check_role


@login_required
def appointment_list(request):
    """List appointments based on role"""

    user_profile = request.user.profile

    if user_profile.role in ['receptionist', 'admin']:
        appointments = Appointment.objects.all()


    elif user_profile.role == 'doctor':

        doctor = Doctor.objects.filter(user=request.user).first()

        appointments = doctor.appointments.all() if doctor else Appointment.objects.none()

    elif user_profile.role == 'patient':
        try:
            patient = request.user.patient_profile
            appointments = patient.appointments.all()
        except:
            appointments = Appointment.objects.none()

    else:
        appointments = Appointment.objects.none()

    search_query = request.GET.get('search', '')

    if search_query:
        appointments = appointments.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(doctor__first_name__icontains=search_query)
        )

    context = {
        'appointments': appointments.order_by('-appointment_date'),
        'search_query': search_query
    }

    return render(request, 'appointments/appointment_list.html', context)


@login_required
@check_role('receptionist')
def appointment_create(request):
    """Create new appointment"""
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        doctor_id = request.POST.get('doctor_id')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        reason = request.POST.get('reason')
        notes = request.POST.get('notes')

        try:
            patient = Patient.objects.get(id=patient_id)
            doctor = Doctor.objects.get(id=doctor_id)
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                reason=reason,
                notes=notes,
                created_by=request.user,
            )
            messages.success(request, 'Appointment created successfully!')
            return redirect('appointments:appointment_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    context = {'patients': Patient.objects.all(), 'doctors': Doctor.objects.all()}
    return render(request, 'appointments/appointment_form.html', context)


@login_required
@check_role('receptionist')
def appointment_edit(request, pk):
    """Edit appointment"""
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.method == 'POST':
        appointment.appointment_date = request.POST.get('appointment_date', appointment.appointment_date)
        appointment.appointment_time = request.POST.get('appointment_time', appointment.appointment_time)
        appointment.reason = request.POST.get('reason', appointment.reason)
        appointment.notes = request.POST.get('notes', appointment.notes)
        appointment.status = request.POST.get('status', appointment.status)
        try:
            appointment.save()
            messages.success(request, 'Appointment updated successfully!')
            return redirect('appointments:appointment_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    context = {'appointment': appointment, 'patients': Patient.objects.all(), 'doctors': Doctor.objects.all()}
    return render(request, 'appointments/appointment_form.html', context)


@login_required
def appointment_detail(request, pk):
    """View appointment details"""
    appointment = get_object_or_404(Appointment, pk=pk)
    context = {'appointment': appointment}
    return render(request, 'appointments/appointment_detail.html', context)


@login_required
@check_role('receptionist')
def appointment_delete(request, pk):
    """Delete appointment"""
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, 'Appointment deleted successfully!')
        return redirect('appointments:appointment_list')
    return render(request, 'appointments/appointment_confirm_delete.html', {'appointment': appointment})




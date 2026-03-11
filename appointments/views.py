from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Appointment, Referral
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


@login_required
@check_role('doctor')
def refer_patient(request, appointment_id):
    """Doctor refers a patient to another doctor"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Make sure only the assigned doctor can refer
    try:
        current_doctor = request.user.doctor_profile
    except Exception:
        messages.error(request, 'Doctor profile not found.')
        return redirect('core:dashboard')

    if appointment.doctor != current_doctor:
        messages.error(request, 'You can only refer your own patients.')
        return redirect('core:dashboard')

    # All other available doctors except the current one
    available_doctors = Doctor.objects.exclude(id=current_doctor.id).filter(is_available=True)

    if request.method == 'POST':
        referred_to_id = request.POST.get('referred_to')
        reason = request.POST.get('reason')
        new_date = request.POST.get('new_date')
        new_time = request.POST.get('new_time')

        if not all([referred_to_id, reason, new_date, new_time]):
            messages.error(request, 'All fields are required.')
            return render(request, 'appointments/refer_patient.html', {
                'appointment': appointment,
                'available_doctors': available_doctors,
            })

        referred_to_doctor = get_object_or_404(Doctor, id=referred_to_id)

        # Create new appointment with the referred doctor
        new_appointment = Appointment.objects.create(
            patient=appointment.patient,
            doctor=referred_to_doctor,
            appointment_date=new_date,
            appointment_time=new_time,
            reason=f"Referred by Dr. {current_doctor.first_name} {current_doctor.last_name}. {reason}",
            status='confirmed',
            created_by=request.user,
        )

        # Create referral record
        Referral.objects.create(
            original_appointment=appointment,
            referred_from=current_doctor,
            referred_to=referred_to_doctor,
            patient=appointment.patient,
            reason=reason,
            new_appointment=new_appointment,
            status='pending',
        )

        # Mark original appointment as referred
        appointment.status = 'referred'
        appointment.save()

        messages.success(
            request,
            f'Patient {appointment.patient} successfully referred to '
            f'Dr. {referred_to_doctor.first_name} {referred_to_doctor.last_name}.'
        )
        return redirect('core:dashboard')

    return render(request, 'appointments/refer_patient.html', {
        'appointment': appointment,
        'available_doctors': available_doctors,
        'current_doctor': current_doctor,
    })


@login_required
def referral_list(request):
    """List referrals - doctors see their own, admins see all"""
    role = request.user.profile.role

    if role == 'admin':
        referrals = Referral.objects.all().select_related(
            'patient', 'referred_from', 'referred_to', 'original_appointment'
        )
    elif role == 'doctor':
        try:
            doctor = request.user.doctor_profile
            referrals = Referral.objects.filter(
                referred_from=doctor
            ).select_related('patient', 'referred_to', 'original_appointment')
        except Exception:
            referrals = Referral.objects.none()
    else:
        return redirect('core:dashboard')

    return render(request, 'appointments/referral_list.html', {'referrals': referrals})

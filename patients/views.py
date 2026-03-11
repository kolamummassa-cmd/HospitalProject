from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from core.views import check_role
from .models import Patient
from core.models import UserProfile
from django.contrib.auth.models import User


@login_required
@check_role('receptionist')
def patient_list(request):
    """List all patients"""
    patients = Patient.objects.all()

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        patients = patients.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(contact__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    context = {
        'patients': patients,
        'search_query': search_query,
    }
    return render(request, 'patients/patient_list.html', context)


@login_required
@check_role('receptionist')
def patient_create(request):
    """Create new patient"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email', '')
        contact = request.POST.get('contact')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')
        blood_type = request.POST.get('blood_type')
        emergency_contact = request.POST.get('emergency_contact')
        emergency_contact_name = request.POST.get('emergency_contact_name')
        medical_history = request.POST.get('medical_history')
        allergies = request.POST.get('allergies')

        try:
            # Create a new user account for the patient
            username = email if email else f"{first_name.lower()}{last_name.lower()}"
            new_user = User.objects.create_user(
                username=username,
                email=email or '',
                password='changeme123',
                first_name=first_name,
                last_name=last_name
            )
            UserProfile.objects.create(user=new_user, role='patient')

            patient = Patient.objects.create(
                user=new_user,        # ← new user, not request.user
                first_name=first_name,
                last_name=last_name,
                email=email,
                contact=contact,
                date_of_birth=date_of_birth,
                gender=gender,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                blood_type=blood_type,
                emergency_contact=emergency_contact,
                emergency_contact_name=emergency_contact_name,
                medical_history=medical_history,
                allergies=allergies,
            )
            messages.success(request, f'Patient {patient} created successfully!')
            return redirect('patients:patient_list')
        except Exception as e:
            messages.error(request, f'Error creating patient: {str(e)}')

    return render(request, 'patients/patient_form.html', {'action': 'Create'})

@login_required
@check_role('receptionist')
def patient_edit(request, pk):
    """Edit patient"""
    patient = get_object_or_404(Patient, pk=pk)

    if request.method == 'POST':
        patient.first_name = request.POST.get('first_name', patient.first_name)
        patient.last_name = request.POST.get('last_name', patient.last_name)
        patient.email = request.POST.get('email', patient.email)
        patient.contact = request.POST.get('contact', patient.contact)
        patient.date_of_birth = request.POST.get('date_of_birth', patient.date_of_birth)
        patient.gender = request.POST.get('gender', patient.gender)
        patient.address = request.POST.get('address', patient.address)
        patient.city = request.POST.get('city', patient.city)
        patient.state = request.POST.get('state', patient.state)
        patient.zip_code = request.POST.get('zip_code', patient.zip_code)
        patient.blood_type = request.POST.get('blood_type', patient.blood_type)
        patient.emergency_contact = request.POST.get('emergency_contact', patient.emergency_contact)
        patient.emergency_contact_name = request.POST.get('emergency_contact_name', patient.emergency_contact_name)
        patient.medical_history = request.POST.get('medical_history', patient.medical_history)
        patient.allergies = request.POST.get('allergies', patient.allergies)

        try:
            patient.save()
            messages.success(request, f'Patient {patient} updated successfully!')
            return redirect('patients:patient_list')
        except Exception as e:
            messages.error(request, f'Error updating patient: {str(e)}')

    context = {
        'patient': patient,
        'action': 'Edit',
    }
    return render(request, 'patients/patient_form.html', context)

@login_required
@check_role('receptionist')
def patient_detail(request, pk):
    """View patient details"""
    patient = get_object_or_404(Patient, pk=pk)

    context = {
        'patient': patient,
        'appointments': patient.appointments.all().order_by('-appointment_date'),
        'visit_history': patient.visit_history.all().order_by('-visit_date'),
    }
    return render(request, 'patients/patient_detail.html', context)


@login_required
@check_role('receptionist')
def patient_delete(request, pk):
    """Delete patient"""
    patient = get_object_or_404(Patient, pk=pk)

    if request.method == 'POST':
        patient_name = str(patient)
        patient.delete()
        messages.success(request, f'Patient {patient_name} deleted successfully!')
        return redirect('patients:patient_list')

    context = {'patient': patient}
    return render(request, 'patients/patient_confirm_delete.html', context)




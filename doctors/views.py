from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Doctor
from core.models import UserProfile
from core.views import check_role


@login_required
@check_role('admin')
def doctor_list(request):
    """List all doctors"""
    doctors = Doctor.objects.all()
    search_query = request.GET.get('search', '')
    if search_query:
        doctors = doctors.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(specialization__icontains=search_query)
        )
    context = {'doctors': doctors, 'search_query': search_query}
    return render(request, 'doctors/doctor_list.html', context)


@login_required
@check_role('admin')
def doctor_create(request):
    """Create new doctor"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        contact = request.POST.get('contact')
        specialization = request.POST.get('specialization')
        license_number = request.POST.get('license_number')
        consultation_fee = request.POST.get('consultation_fee', 0)
        bio = request.POST.get('bio')
        availability = request.POST.get('availability')

        try:
            doctor = Doctor.objects.create(
                user=request.user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                contact=contact,
                specialization=specialization,
                license_number=license_number,
                consultation_fee=consultation_fee,
                bio=bio,
                availability=availability,
            )
            messages.success(request, f'Doctor {doctor} created successfully!')
            return redirect('doctors:doctor_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    return render(request, 'doctors/doctor_form.html', {'action': 'Create'})


@login_required
@check_role('admin')
def doctor_edit(request, pk):
    """Edit doctor"""
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        doctor.first_name = request.POST.get('first_name', doctor.first_name)
        doctor.last_name = request.POST.get('last_name', doctor.last_name)
        doctor.email = request.POST.get('email', doctor.email)
        doctor.contact = request.POST.get('contact', doctor.contact)
        doctor.specialization = request.POST.get('specialization', doctor.specialization)
        doctor.consultation_fee = request.POST.get('consultation_fee', doctor.consultation_fee)
        doctor.bio = request.POST.get('bio', doctor.bio)
        doctor.availability = request.POST.get('availability', doctor.availability)
        try:
            doctor.save()
            messages.success(request, f'Doctor {doctor} updated successfully!')
            return redirect('doctors:doctor_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    context = {'doctor': doctor, 'action': 'Edit'}
    return render(request, 'doctors/doctor_form.html', context)


@login_required
@check_role('admin')
def doctor_delete(request, pk):
    """Delete doctor"""
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        doctor_name = str(doctor)
        doctor.delete()
        messages.success(request, f'Doctor {doctor_name} deleted successfully!')
        return redirect('doctors:doctor_list')
    return render(request, 'doctors/doctor_confirm_delete.html', {'doctor': doctor})




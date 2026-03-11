
from django.contrib import messages

from datetime import timedelta

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.utils import timezone
from functools import wraps

from .models import UserProfile
from patients.models import VisitHistory
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('core:dashboard')
        else:
            return render(request, 'core/login.html', {'error': 'Invalid credentials'})

    return render(request, 'core/login.html')


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        role = request.POST.get('role', 'patient')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        if password != password_confirm:
            return render(request, 'core/register.html', {'error': 'Passwords do not match'})

        if User.objects.filter(username=username).exists():
            return render(request, 'core/register.html', {'error': 'Username already exists'})

        if User.objects.filter(email=email).exists():
            return render(request, 'core/register.html', {'error': 'Email already exists'})

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create user profile
        UserProfile.objects.create(user=user, role=role)

        # Create patient profile if registering as patient
        if role == 'patient':
            Patient.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                date_of_birth='',
                gender='',
                contact='',
                address='',
                county=''


            )

        # Auto-login
        login(request, user)
        return redirect('core:dashboard')

    return render(request, 'core/register.html')


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('core:login')


@login_required
def dashboard(request):
    """Main dashboard - role-specific"""
    user_profile = request.user.profile
    role = user_profile.role
    context = {'role': role}

    if role == 'admin':
        # Admin dashboard with statistics
        context.update({
            'total_patients': Patient.objects.count(),
            'total_doctors': Doctor.objects.count(),
            'total_appointments': Appointment.objects.count(),
            'pending_appointments': Appointment.objects.filter(status='pending').count(),
            'completed_appointments': Appointment.objects.filter(status='completed').count(),
            'cancelled_appointments': Appointment.objects.filter(status='cancelled').count(),
        })

        # Today's appointments
        today = timezone.now().date()
        context['todays_appointments'] = Appointment.objects.filter(
            appointment_date=today
        ).select_related('patient', 'doctor')[:10]

    elif role == 'doctor':

        try:



            doctor = request.user.doctor_profile

            today = timezone.now().date()

            next_week = today + timedelta(days=7)

            # All doctor's appointments

            all_apts = doctor.appointments.all()

            total_completed = all_apts.filter(status='completed').count()

            total_all = all_apts.count()

            # Completion rate

            completion_rate = round((total_completed / total_all * 100), 1) if total_all > 0 else 0

            # Today's appointments ordered by time

            todays_apts = all_apts.filter(

                appointment_date=today

            ).select_related('patient').order_by('appointment_time')

            # Upcoming next 7 days (excluding today)

            upcoming_week = all_apts.filter(

                appointment_date__gt=today,

                appointment_date__lte=next_week

            ).select_related('patient').order_by('appointment_date', 'appointment_time')

            # My unique patients



            patient_ids = all_apts.values_list('patient_id', flat=True).distinct()

            my_patients = Patient.objects.filter(id__in=patient_ids)[:8]

            context.update({

                'doctor': doctor,

                'todays_appointments': todays_apts,

                'pending_appointments': all_apts.filter(status='pending').count(),

                'total_patients': patient_ids.count(),

                'total_completed': total_completed,

                'completion_rate': completion_rate,

                'upcoming_week': upcoming_week,

                'my_patients': my_patients,

            })

        except Exception:

            pass

    elif role == 'receptionist':

        today = timezone.now().date()

        todays_apts = Appointment.objects.filter(

            appointment_date=today

        ).select_related('patient', 'doctor').order_by('appointment_time')

        context.update({

            'total_patients': Patient.objects.count(),

            'total_doctors': Doctor.objects.count(),

            'total_appointments': Appointment.objects.count(),

            'pending_appointments': Appointment.objects.filter(status='pending').count(),

            # Today's queue ordered by time

            'todays_appointments': todays_apts,

            # Confirmed appointments today

            'todays_confirmed': todays_apts.filter(status='confirmed').count(),

            # Cancelled appointments today - for alert banner

            'todays_cancelled': todays_apts.filter(status='cancelled').count(),

            # Pending appointments needing confirmation

            'pending_confirmation': Appointment.objects.filter(

                status='pending'

            ).select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')[:10],

            # Recently registered patients

            'recent_patients': Patient.objects.order_by('-created_at')[:5],

    })

    elif role == 'patient':
        # Patient dashboard
        try:
            patient = request.user.patient_profile
            context.update({
                'patient': patient,
                'upcoming_appointments': patient.appointments.filter(
                    appointment_date__gte=timezone.now().date(),
                    status__in=['pending', 'confirmed', 'scheduled']
                ).select_related('doctor')[:5],
                'recent_visits': VisitHistory.objects.filter(patient=patient)[:5],
            })
        except Patient.DoesNotExist:
            pass

    return render(request, 'core/dashboard.html', context)


@login_required
def profile_view(request):
    """User profile view"""
    user_profile = request.user.profile

    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', request.user.first_name)
        request.user.last_name = request.POST.get('last_name', request.user.last_name)
        request.user.email = request.POST.get('email', request.user.email)
        request.user.save()

        user_profile.phone = request.POST.get('phone', user_profile.phone)
        user_profile.address = request.POST.get('address', user_profile.address)
        user_profile.city = request.POST.get('city', user_profile.city)
        user_profile.state = request.POST.get('state', user_profile.state)
        user_profile.zip_code = request.POST.get('zip_code', user_profile.zip_code)
        user_profile.save()

        return redirect('core:profile')

    context = {
        'user_profile': user_profile,
    }
    return render(request, 'core/profile.html', context)


def check_role(role):
    """Decorator to check user role"""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('core:login')
            if request.user.profile.role != role and request.user.profile.role != 'admin':
                return redirect('core:dashboard')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator



@login_required
@check_role('admin')
def staff_list(request):
    """List all staff - doctors and receptionists"""
    staff = UserProfile.objects.filter(
        role__in=['doctor', 'receptionist']
    ).select_related('user')
    return render(request, 'core/staff_list.html', {'staff': staff})


@login_required
@check_role('admin')
def staff_create(request):
    """Admin creates a receptionist or doctor account"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role')  # 'receptionist' or 'doctor'

        try:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
            else:
                new_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                UserProfile.objects.create(user=new_user, role=role)
                messages.success(request, f'{role.title()} account created successfully!')
                return redirect('core:staff_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')

    return render(request, 'core/staff_form.html')


@login_required
@check_role('admin')
def staff_delete(request, pk):
    """Delete a staff account"""
    profile = get_object_or_404(UserProfile, pk=pk)
    if request.method == 'POST':
        profile.user.delete()
        messages.success(request, 'Staff account deleted successfully!')
        return redirect('core:staff_list')
    return render(request, 'core/staff_confirm_delete.html', {'profile': profile})
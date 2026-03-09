from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile, Patient, Doctor, Appointment, VisitHistory


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
                date_of_birth='2000-01-01',
                gender='male',
                contact='',
                address='',
                city='',
                state='',
                zip_code=''
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
        # Doctor dashboard
        try:
            doctor = request.user.doctor_profile
            context.update({
                'doctor': doctor,
                'todays_appointments': doctor.appointments.filter(
                    appointment_date=timezone.now().date()
                ).select_related('patient'),
                'pending_appointments': doctor.appointments.filter(status='pending').count(),
                'total_patients': doctor.appointments.values('patient').distinct().count(),
            })
        except Doctor.DoesNotExist:
            pass

    elif role == 'receptionist':
        # Receptionist dashboard
        context.update({
            'total_patients': Patient.objects.count(),
            'total_doctors': Doctor.objects.count(),
            'total_appointments': Appointment.objects.count(),
            'pending_appointments': Appointment.objects.filter(status='pending').count(),
        })

        today = timezone.now().date()
        context['todays_appointments'] = Appointment.objects.filter(
            appointment_date=today
        ).select_related('patient', 'doctor')[:10]

    elif role == 'patient':
        # Patient dashboard
        try:
            patient = request.user.patient_profile
            context.update({
                'patient': patient,
                'upcoming_appointments': patient.appointments.filter(
                    appointment_date__gte=timezone.now().date(),
                    status__in=['pending', 'completed']
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
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('core:login')
            if request.user.profile.role != role and request.user.profile.role != 'admin':
                return redirect('core:dashboard')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator




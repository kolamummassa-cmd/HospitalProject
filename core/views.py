from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from functools import wraps

from .models import UserProfile
from patients.models import Patient, VisitHistory
from doctors.models import Doctor
from appointments.models import Appointment


# ─────────────────────────────────────────────
# AUTH VIEWS
# ─────────────────────────────────────────────

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
    """User registration view - for patients only"""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        date_of_birth = request.POST.get('date_of_birth', '')
        gender = request.POST.get('gender', '')
        contact = request.POST.get('contact', '')
        address = request.POST.get('address', '')
        county = request.POST.get('county', '')

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

        # Create user profile as patient
        UserProfile.objects.create(user=user, role='patient')

        # Create patient profile with correct fields
        Patient.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth or '2000-01-01',
            gender=gender or 'other',
            contact=contact or '0000000000',
            address=address or '',
            county=county or '',
        )

        login(request, user)
        return redirect('core:dashboard')

    return render(request, 'core/register.html')


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('core:login')


# ─────────────────────────────────────────────
# ROLE DECORATOR
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard - role-specific content"""
    user_profile = request.user.profile
    role = user_profile.role
    context = {'role': role}

    # ── ADMIN ──────────────────────────────────
    if role == 'admin':
        today = timezone.now().date()
        context.update({
            'total_patients': Patient.objects.count(),
            'total_doctors': Doctor.objects.count(),
            'total_appointments': Appointment.objects.count(),
            'pending_appointments': Appointment.objects.filter(status='pending').count(),
            'completed_appointments': Appointment.objects.filter(status='completed').count(),
            'cancelled_appointments': Appointment.objects.filter(status='cancelled').count(),
            'todays_appointments': Appointment.objects.filter(
                appointment_date=today
            ).select_related('patient', 'doctor').order_by('appointment_time'),
            'recent_patients': Patient.objects.order_by('-created_at')[:5],
        })

    # ── DOCTOR ─────────────────────────────────
    elif role == 'doctor':
        today = timezone.now().date()
        next_week = today + timedelta(days=7)

        # Get the Doctor record linked to this logged-in user
        doctor = Doctor.objects.filter(user=request.user).first()

        if doctor is None:
            # Doctor record not found - show warning in context
            context['doctor_not_found'] = True
        else:
            all_apts = Appointment.objects.filter(doctor=doctor)
            total_completed = all_apts.filter(status='completed').count()
            total_all = all_apts.count()
            completion_rate = round((total_completed / total_all * 100), 1) if total_all > 0 else 0

            todays_apts = all_apts.filter(
                appointment_date=today
            ).select_related('patient').order_by('appointment_time')

            upcoming_week = all_apts.filter(
                appointment_date__gt=today,
                appointment_date__lte=next_week
            ).select_related('patient').order_by('appointment_date', 'appointment_time')

            patient_ids = all_apts.values_list('patient_id', flat=True).distinct()
            my_patients = Patient.objects.filter(id__in=patient_ids)[:8]

            from appointments.models import Referral
            referrals_made = Referral.objects.filter(
                referred_from=doctor
            ).select_related('patient', 'referred_to', 'new_appointment').order_by('-created_at')[:5]

            context.update({
                'doctor': doctor,
                'todays_appointments': todays_apts,
                'pending_appointments': all_apts.filter(status='pending').count(),
                'total_patients': patient_ids.count(),
                'total_completed': total_completed,
                'completion_rate': completion_rate,
                'upcoming_week': upcoming_week,
                'my_patients': my_patients,
                'referrals_made': referrals_made,
            })

    # ── RECEPTIONIST ───────────────────────────
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
            'todays_appointments': todays_apts,
            'todays_confirmed': todays_apts.filter(status='confirmed').count(),
            'todays_cancelled': todays_apts.filter(status='cancelled').count(),
            'pending_confirmation': Appointment.objects.filter(
                status='pending'
            ).select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')[:10],
            'recent_patients': Patient.objects.order_by('-created_at')[:5],
        })

    # ── PATIENT ────────────────────────────────
    elif role == 'patient':
        today = timezone.now().date()

        patient = Patient.objects.filter(user=request.user).first()

        if patient is None:
            context['patient_not_found'] = True
        else:
            all_apts = Appointment.objects.filter(patient=patient).select_related('doctor')

            upcoming = all_apts.filter(
                appointment_date__gte=today
            ).exclude(status='cancelled').order_by('appointment_date', 'appointment_time')

            past = all_apts.filter(
                appointment_date__lt=today
            ).order_by('-appointment_date')[:10]

            next_appointment = upcoming.first()

            visit_history = VisitHistory.objects.filter(
                patient=patient
            ).select_related('doctor').order_by('-visit_date')[:10]

            from appointments.models import Referral
            patient_referrals = Referral.objects.filter(
                patient=patient
            ).select_related('referred_from', 'referred_to', 'new_appointment').order_by('-created_at')[:3]

            context.update({
                'patient': patient,
                'upcoming_appointments': upcoming,
                'past_appointments': past,
                'next_appointment': next_appointment,
                'visit_history': visit_history,
                'latest_prescription': visit_history.first(),
                'total_visits': all_apts.count(),
                'completed_visits': all_apts.filter(status='completed').count(),
                'cancelled_appointments': all_apts.filter(status='cancelled').count(),
                'patient_referrals': patient_referrals,
            })

    return render(request, 'core/dashboard.html', context)


# ─────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────

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

    return render(request, 'core/profile.html', {'user_profile': user_profile})


# ─────────────────────────────────────────────
# STAFF MANAGEMENT
# ─────────────────────────────────────────────

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
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        else:
            try:
                new_user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                UserProfile.objects.create(user=new_user, role=role)
                messages.success(request, f'{role.title()} account created! '
                                          f'Login: {username} / {password}')
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
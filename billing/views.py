from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from core.views import check_role
from .models import Bill, BillItem, Payment
from appointments.models import Appointment

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django_daraja.mpesa.core import MpesaClient



@login_required
@check_role('receptionist')
def bill_list(request):
    """List all bills"""
    role = request.user.profile.role

    if role == 'admin':
        bills = Bill.objects.all().select_related('patient', 'doctor', 'appointment')
    else:
        bills = Bill.objects.all().select_related('patient', 'doctor', 'appointment')

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        bills = bills.filter(status=status_filter)

    # Search
    search = request.GET.get('search', '')
    if search:
        bills = bills.filter(
            patient__first_name__icontains=search
        ) | bills.filter(
            patient__last_name__icontains=search
        )

    context = {
        'bills': bills,
        'status_filter': status_filter,
        'search': search,
        'total_pending': Bill.objects.filter(status='pending').count(),
        'total_sent': Bill.objects.filter(status='sent').count(),
        'total_paid': Bill.objects.filter(status='paid').count(),
    }
    return render(request, 'billing/bill_list.html', context)


@login_required
@check_role('receptionist')
def bill_create(request, appointment_id):
    """Create a bill for a completed appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Check bill doesn't already exist
    if hasattr(appointment, 'bill'):
        messages.warning(request, 'A bill already exists for this appointment.')
        return redirect('billing:bill_detail', pk=appointment.bill.id)

    if request.method == 'POST':
        discount = request.POST.get('discount', 0)
        notes = request.POST.get('notes', '')

        # Create bill
        bill = Bill.objects.create(
            appointment=appointment,
            patient=appointment.patient,
            doctor=appointment.doctor,
            discount=discount or 0,
            notes=notes,
            status='pending',
        )

        # Add consultation fee automatically
        Bill.objects.filter(id=bill.id)  # refresh
        BillItem.objects.create(
            bill=bill,
            category='consultation',
            description=f'Consultation with Dr. {appointment.doctor.first_name} {appointment.doctor.last_name}',
            quantity=1,
            unit_price=appointment.doctor.consultation_fee or 0,
        )

        # Add extra items
        descriptions = request.POST.getlist('description')
        categories = request.POST.getlist('category')
        quantities = request.POST.getlist('quantity')
        unit_prices = request.POST.getlist('unit_price')

        for i in range(len(descriptions)):
            if descriptions[i].strip():
                BillItem.objects.create(
                    bill=bill,
                    category=categories[i] if i < len(categories) else 'other',
                    description=descriptions[i],
                    quantity=int(quantities[i]) if i < len(quantities) and quantities[i] else 1,
                    unit_price=float(unit_prices[i]) if i < len(unit_prices) and unit_prices[i] else 0,
                )

        messages.success(request, f'Bill #{bill.id} created successfully!')
        return redirect('billing:bill_detail', pk=bill.id)

    # Pre-fill consultation fee
    context = {
        'appointment': appointment,
        'consultation_fee': appointment.doctor.consultation_fee or 0,
        'categories': BillItem.CATEGORY_CHOICES,
    }
    return render(request, 'billing/bill_form.html', context)


@login_required
def bill_detail(request, pk):
    """View bill details"""
    bill = get_object_or_404(Bill, pk=pk)
    role = request.user.profile.role

    # Patients can only see their own bills
    if role == 'patient':
        try:
            if bill.patient.user != request.user:
                messages.error(request, 'You can only view your own bills.')
                return redirect('core:dashboard')
        except Exception:
            return redirect('core:dashboard')

    return render(request, 'billing/bill_detail.html', {'bill': bill})


@login_required
@check_role('receptionist')
def bill_mark_sent(request, pk):
    """Mark bill as sent to patient"""
    bill = get_object_or_404(Bill, pk=pk)
    bill.status = 'sent'
    bill.save()
    messages.success(request, f'Bill #{bill.id} marked as sent.')
    return redirect('billing:bill_detail', pk=bill.id)


@login_required
@check_role('receptionist')
def bill_mark_paid(request, pk):
    """Mark bill as paid"""
    bill = get_object_or_404(Bill, pk=pk)
    bill.status = 'paid'
    bill.paid_at = timezone.now()
    bill.save()
    messages.success(request, f'Bill #{bill.id} marked as paid!')
    return redirect('billing:bill_detail', pk=bill.id)


@login_required
@check_role('receptionist')
def bill_add_item(request, pk):
    """Add an item to an existing bill"""
    bill = get_object_or_404(Bill, pk=pk)

    if bill.status == 'paid':
        messages.error(request, 'Cannot modify a paid bill.')
        return redirect('billing:bill_detail', pk=bill.id)

    if request.method == 'POST':
        BillItem.objects.create(
            bill=bill,
            category=request.POST.get('category', 'other'),
            description=request.POST.get('description'),
            quantity=int(request.POST.get('quantity', 1)),
            unit_price=float(request.POST.get('unit_price', 0)),
        )
        messages.success(request, 'Item added to bill.')

    return redirect('billing:bill_detail', pk=bill.id)


@login_required
@check_role('receptionist')
def bill_delete_item(request, item_id):
    """Delete a bill item"""
    item = get_object_or_404(BillItem, id=item_id)
    bill_id = item.bill.id

    if item.bill.status == 'paid':
        messages.error(request, 'Cannot modify a paid bill.')
        return redirect('billing:bill_detail', pk=bill_id)

    item.delete()
    messages.success(request, 'Item removed.')
    return redirect('billing:bill_detail', pk=bill_id)


@login_required
def bill_print(request, pk):
    """Printable invoice view"""
    bill = get_object_or_404(Bill, pk=pk)
    return render(request, 'billing/bill_print.html', {'bill': bill})


# ── ADD THESE IMPORTS at the top of your existing views.py ──



# ── Pay Now — Triggers STK Push to patient's phone ──


@login_required
@check_role('receptionist')
def bill_pay_now(request, pk):
    bill = get_object_or_404(Bill, pk=pk)

    if bill.status == 'paid':
        return JsonResponse({'success': False, 'message': 'This bill is already paid.'})

    if request.method == 'POST':
        phone_number = request.POST.get('mpesa_number', '').strip()

        if not phone_number:
            return JsonResponse({'success': False, 'message': 'Please enter an M-Pesa number.'})

        try:
            client = MpesaClient()
            response = client.stk_push(
                phone_number,
                int(bill.total),
                'ApexCareHMS',
                f'Payment for Bill #{bill.id}',
                settings.MPESA_CALLBACK_URL
            ).json()

            print("STK Push response:", response)

            checkout_request_id = response.get('CheckoutRequestID', '')

            # Save pending payment
            Payment.objects.update_or_create(
                bill=bill,
                defaults={
                    'amount_paid': bill.total,
                    'payment_method': 'mpesa',
                    'mpesa_number': phone_number,
                    'payment_status': 'pending',
                    'transaction_code': checkout_request_id,
                    'recorded_by': request.user,
                }
            )

            return JsonResponse({
                'success': True,
                'message': '✅ STK Push sent! Check your phone and enter your M-Pesa PIN.'
            })

        except Exception as e:
            print("STK Push error:", str(e))
            return JsonResponse({
                'success': False,
                'message': f'Payment failed: {str(e)}'
            })

    return redirect('billing:bill_detail', pk=bill.id)


# ── M-Pesa Callback — Safaricom calls this automatically after payment ──
@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            data        = json.loads(request.body)
            result      = data['Body']['stkCallback']
            result_code = result['ResultCode']
            checkout_id = result['CheckoutRequestID']

            # Find payment by checkout request id
            payment = Payment.objects.filter(
                transaction_code=checkout_id
            ).first()

            if not payment:
                return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})

            if result_code == 0:
                # ✅ Payment successful
                items = result['CallbackMetadata']['Item']
                meta  = {item['Name']: item.get('Value') for item in items}

                transaction_code = meta.get('MpesaReceiptNumber')
                amount           = meta.get('Amount')
                phone            = str(meta.get('PhoneNumber'))

                payment.transaction_code = transaction_code
                payment.mpesa_number     = phone
                payment.amount_paid      = amount
                payment.payment_status   = 'completed'
                payment.save()

                # Mark bill as paid
                payment.bill.status  = 'paid'
                payment.bill.paid_at = timezone.now()
                payment.bill.save()

            else:
                # ❌ Failed or cancelled
                payment.payment_status = 'failed'
                payment.save()

        except Exception as e:
            print(f"Callback error: {e}")

    return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})
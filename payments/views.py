from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.conf import settings
from .models import Payment, Refund
from .forms import PaymentForm, RefundRequestForm, PaymentVerificationForm
from bookings.models import Booking
import uuid
import json

@login_required
def process_payment(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id)
    booking = payment.booking
    
    # Ensure the payment belongs to the logged-in user
    if booking.user != request.user:
        messages.error(request, 'You do not have permission to access this payment.')
        return redirect('accounts:booking_history')
    
    # Check if payment is already completed
    if payment.payment_status == 'completed':
        messages.info(request, 'This payment has already been completed.')
        return redirect('payment_success', payment_id=payment_id)
    
    if request.method == 'POST':
        # Handle AJAX payment processing
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            try:
                with transaction.atomic():
                    # Get payment method from POST data
                    payment_method = request.POST.get('payment_method')
                    
                    # Simulate payment processing (in real implementation, integrate with payment gateway)
                    payment.transaction_id = f'TX{uuid.uuid4().hex[:8].upper()}'
                    payment.payment_date = timezone.now()
                    payment.payment_method = payment_method
                    payment.payment_status = 'completed'
                    payment.save()
                    
                    # Update booking payment status
                    booking.payment_status = 'paid'
                    booking.booking_status = 'confirmed'
                    booking.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Payment completed successfully!',
                        'redirect_url': reverse('bookings:booking_confirmation', args=[booking.booking_id])
                    })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error processing payment: {str(e)}'
                })
        
        # Handle regular form submission
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Update payment details
                    payment.transaction_id = form.cleaned_data.get('transaction_id', f'TX{uuid.uuid4().hex[:8].upper()}')
                    payment.payment_date = timezone.now()
                    payment.payment_status = 'completed'
                    payment.save()
                    
                    # Update booking payment status
                    booking.payment_status = 'paid'
                    booking.booking_status = 'confirmed'
                    booking.save()
                    
                    messages.success(request, 'Payment completed successfully!')
                    return redirect('bookings:booking_confirmation', booking_id=booking.booking_id)
            except Exception as e:
                messages.error(request, f'Error processing payment: {str(e)}')
                return redirect('payments:process_payment', payment_id=payment_id)
    else:
        form = PaymentForm(initial={'payment_method': payment.payment_method})
    
    context = {
        'payment': payment,
        'booking': booking,
        'form': form,
    }
    
    return render(request, 'payments/process_payment.html', context)

@login_required
def payment_success(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id, payment_status='completed')
    booking = payment.booking
    
    # Ensure the payment belongs to the logged-in user
    if booking.user != request.user:
        messages.error(request, 'You do not have permission to access this payment.')
        return redirect('booking_history')
    
    context = {
        'payment': payment,
        'booking': booking,
    }
    
    return render(request, 'payments/payment_success.html', context)

@login_required
def payment_history(request):
    payments = Payment.objects.filter(booking__user=request.user).order_by('-payment_date')
    
    context = {
        'payments': payments,
    }
    
    return render(request, 'payments/payment_history.html', context)

@login_required
def payment_detail(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id)
    booking = payment.booking
    
    # Ensure the payment belongs to the logged-in user
    if booking.user != request.user:
        messages.error(request, 'You do not have permission to access this payment.')
        return redirect('accounts:payment_history')
    
    # Get refund if exists
    refund = Refund.objects.filter(payment=payment).first()
    
    context = {
        'payment': payment,
        'booking': booking,
        'refund': refund,
    }
    
    return render(request, 'payments/payment_detail.html', context)

@login_required
def request_refund(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id, payment_status='completed')
    booking = payment.booking
    
    # Ensure the payment belongs to the logged-in user
    if booking.user != request.user:
        messages.error(request, 'You do not have permission to request a refund for this payment.')
        return redirect('accounts:payment_history')
    
    # Check if refund already exists
    existing_refund = Refund.objects.filter(payment=payment).first()
    if existing_refund:
        messages.info(request, f'A refund request already exists with status: {existing_refund.get_refund_status_display()}')
        return redirect('payment_detail', payment_id=payment_id)
    
    # Check if booking is cancelled
    if booking.booking_status != 'cancelled':
        messages.error(request, 'You must cancel your booking before requesting a refund.')
        return redirect('bookings:booking_detail', booking_id=booking.booking_id)
    
    if request.method == 'POST':
        form = RefundRequestForm(request.POST)
        if form.is_valid():
            try:
                # Calculate refund amount (e.g., 90% of total fare)
                refund_amount = booking.total_fare * 0.9
                
                # Create refund
                refund = Refund.objects.create(
                    payment=payment,
                    amount=refund_amount,
                    reason=form.cleaned_data['reason'],
                    refund_status='pending'
                )
                
                messages.success(request, 'Refund request submitted successfully. It will be processed within 7-10 business days.')
                return redirect('payment_detail', payment_id=payment_id)
            except Exception as e:
                messages.error(request, f'Error requesting refund: {str(e)}')
                return redirect('request_refund', payment_id=payment_id)
    else:
        form = RefundRequestForm()
    
    context = {
        'payment': payment,
        'booking': booking,
        'form': form,
    }
    
    return render(request, 'payments/request_refund.html', context)

def verify_payment(request):
    if request.method == 'POST':
        form = PaymentVerificationForm(request.POST)
        if form.is_valid():
            payment_id = form.cleaned_data['payment_id']
            transaction_id = form.cleaned_data['transaction_id']
            
            try:
                payment = Payment.objects.get(payment_id=payment_id, transaction_id=transaction_id)
                
                data = {
                    'verified': True,
                    'payment_status': payment.payment_status,
                    'payment_date': payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else None,
                    'amount': float(payment.amount),
                    'booking_id': payment.booking.booking_id,
                }
                
                return JsonResponse(data)
            except Payment.DoesNotExist:
                return JsonResponse({'verified': False, 'error': 'Payment not found or transaction ID does not match'})
    else:
        form = PaymentVerificationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'payments/verify_payment.html', context)

# Admin views for payment management
@login_required
def admin_refund_list(request):
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home:home')
    
    refunds = Refund.objects.all().order_by('-refund_date')
    
    # Filter by status if provided
    status = request.GET.get('status')
    if status:
        refunds = refunds.filter(refund_status=status)
    
    context = {
        'refunds': refunds,
    }
    
    return render(request, 'payments/admin_refund_list.html', context)

@login_required
def admin_process_refund(request, refund_id):
    # Check if user is staff
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home:home')
    
    refund = get_object_or_404(Refund, id=refund_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            refund.refund_status = 'COMPLETED'
            refund.processed_date = timezone.now()
            refund.save()
            messages.success(request, f'Refund #{refund.id} has been approved and marked as completed.')
        elif action == 'reject':
            refund.refund_status = 'REJECTED'
            refund.processed_date = timezone.now()
            refund.save()
            messages.success(request, f'Refund #{refund.id} has been rejected.')
        
        return redirect('payments:admin_refund_list')
    
    context = {
        'refund': refund,
    }
    
    return render(request, 'payments/admin_process_refund.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Payment, Refund
from .forms import PaymentForm, RefundRequestForm, PaymentVerificationForm
from .esewa_utils import prepare_esewa_payment_data, verify_esewa_payment, EsewaConfig
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
                    
                    # Handle eSewa payment (only supported method)
                    if payment_method == 'esewa':
                        # Update payment method
                        payment.payment_method = payment_method
                        payment.save()
                        
                        # Prepare eSewa payment data
                        esewa_data = prepare_esewa_payment_data(payment, booking)
                        
                        return JsonResponse({
                            'success': True,
                            'payment_method': 'esewa',
                            'esewa_data': esewa_data,
                            'esewa_url': EsewaConfig.get_payment_url(),
                            'message': 'Redirecting to eSewa payment gateway...'
                        })
                    
                    # If unsupported method is provided, return error
                    return JsonResponse({
                        'success': False,
                        'error': 'Unsupported payment method. Only eSewa is accepted.'
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
                
                messages.success(request, 'Refund request submitted successfully. eSewa refunds are typically processed within 1-2 business days.')
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

@csrf_exempt
@require_http_methods(["GET", "POST"])
def esewa_success(request):
    """
    Handle eSewa payment success callback
    """
    try:
        # Get payment data from request
        if request.method == 'POST':
            payment_data = request.POST.dict()
        else:
            payment_data = request.GET.dict()
        
        # Extract transaction UUID (payment ID)
        transaction_uuid = payment_data.get('transaction_uuid')
        if not transaction_uuid:
            messages.error(request, 'Invalid payment response from eSewa.')
            return redirect('accounts:booking_history')
        
        # Get payment object
        try:
            payment = Payment.objects.get(payment_id=transaction_uuid)
        except Payment.DoesNotExist:
            messages.error(request, 'Payment not found.')
            return redirect('accounts:booking_history')
        
        # Verify payment signature
        if verify_esewa_payment(payment_data):
            with transaction.atomic():
                # Update payment status
                payment.transaction_id = payment_data.get('transaction_code', f'ESW{uuid.uuid4().hex[:8].upper()}')
                payment.payment_date = timezone.now()
                payment.payment_status = 'completed'
                payment.save()
                
                # Update booking status and reserve seats
                booking = payment.booking
                booking.payment_status = 'paid'
                booking.booking_status = 'confirmed'
                booking.save()
                
                # Mark seats as unavailable now that payment is confirmed
                for seat in booking.seats.all():
                    seat.is_available = False
                    seat.save()
                
                messages.success(request, 'Payment completed successfully via eSewa!')
                return redirect('bookings:booking_confirmation', booking_id=booking.booking_id)
        else:
            # Payment verification failed
            with transaction.atomic():
                payment.payment_status = 'failed'
                payment.save()
                
                # Cancel the booking since payment failed
                booking = payment.booking
                booking.payment_status = 'failed'
                booking.booking_status = 'cancelled'
                booking.save()
                
                # Note: Seats remain available since they were never marked as unavailable
                
            messages.error(request, 'Payment verification failed. Your booking has been cancelled. Please try again.')
            return redirect('accounts:booking_history')
            
    except Exception as e:
        messages.error(request, f'Error processing eSewa payment: {str(e)}')
        return redirect('accounts:booking_history')

@csrf_exempt
@require_http_methods(["GET", "POST"])
def esewa_failure(request):
    """
    Handle eSewa payment failure callback
    """
    try:
        # Get payment data from request
        if request.method == 'POST':
            payment_data = request.POST.dict()
        else:
            payment_data = request.GET.dict()
        
        # Extract transaction UUID (payment ID)
        transaction_uuid = payment_data.get('transaction_uuid')
        if transaction_uuid:
            try:
                with transaction.atomic():
                    payment = Payment.objects.get(payment_id=transaction_uuid)
                    payment.payment_status = 'failed'
                    payment.save()
                    
                    # Cancel the booking since payment failed
                    booking = payment.booking
                    booking.payment_status = 'failed'
                    booking.booking_status = 'cancelled'
                    booking.save()
                    
                    # Note: Seats remain available since they were never marked as unavailable
            except Payment.DoesNotExist:
                pass
        
        messages.error(request, 'Payment was cancelled or failed. Please try again.')
        
        # Redirect to payment page if payment ID is available
        if transaction_uuid:
            return redirect('payments:process_payment', payment_id=transaction_uuid)
        else:
            return redirect('accounts:booking_history')
            
    except Exception as e:
        messages.error(request, f'Error handling payment failure: {str(e)}')
        return redirect('accounts:booking_history')

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
            refund.refund_status = 'processed'
            refund.processed_date = timezone.now()
            refund.save()
            messages.success(request, f'Refund #{refund.id} has been approved and marked as processed.')
        elif action == 'reject':
            refund.refund_status = 'rejected'
            refund.processed_date = timezone.now()
            refund.save()
            messages.success(request, f'Refund #{refund.id} has been rejected.')
        
        return redirect('payments:admin_refund_list')
    
    context = {
        'refund': refund,
    }
    
    return render(request, 'payments/admin_process_refund.html', context)


@login_required
def payment_form(request, booking_id):
    """
    Display a simple wrapper page for initiating or retrying a payment by booking_id.
    This view will locate an existing pending/failed payment for the booking or
    create a new pending Payment record and then render the payment_form.html
    which posts to the process_payment endpoint.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)

    # Ensure the booking belongs to the logged-in user
    if booking.user != request.user:
        messages.error(request, 'You do not have permission to access this booking payment.')
        return redirect('accounts:booking_history')

    # Try to find an existing payment that can be retried (pending or failed)
    payment = (
        booking.payments.filter(payment_status__in=['pending', 'failed'])
        .order_by('-updated_at')
        .first()
    )

    if not payment:
        # If none exists, create a fresh pending payment
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_fare,
            payment_method=booking.payment_method or 'esewa',
            payment_status='pending',
        )

    context = {
        'booking': booking,
        'payment': payment,
        'retry': request.GET.get('retry') == '1',
    }

    return render(request, 'payments/payment_form.html', context)

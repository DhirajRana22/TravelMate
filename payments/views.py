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
from .esewa_utils import prepare_esewa_payment_data, verify_esewa_payment, EsewaConfig, query_esewa_status
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)
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
                        request.session['pending_payment_id'] = str(payment.payment_id)
                        
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
        
        # Disallow non-AJAX completion to enforce eSewa success validation
        messages.error(request, 'Invalid payment submission. Please complete payment via eSewa.')
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
    Ensure booking and payment status are updated correctly after payment verification.
    """
    try:
        # Get payment data from request
        payment_data = request.POST.dict() if request.method == 'POST' else request.GET.dict()
        # Decode eSewa's base64 'data' envelope if present
        if payment_data.get('data'):
            try:
                import base64, json
                decoded = base64.b64decode(payment_data['data']).decode('utf-8')
                parsed = json.loads(decoded)
                payment_data.update(parsed)
            except Exception:
                pass
        transaction_uuid = payment_data.get('oid') or payment_data.get('transaction_uuid') or request.session.get('pending_payment_id')
        if not transaction_uuid:
            messages.error(request, 'Invalid payment response from eSewa.')
            logger.error('eSewa success missing transaction_uuid and session fallback.')
            return redirect('accounts:booking_history')

        # --- ROBUST PAYMENT VERIFICATION ---
        # We perform two checks: a reliable server-to-server query and a secondary local signature check.
        status_ok = False
        payment = None
        
        try:
            # Use our database as the source of truth for the payment object.
            from .models import Payment
            payment = Payment.objects.get(payment_id=transaction_uuid)
            
            # Perform the server-to-server query using the amount from our database.
            status_result = query_esewa_status(transaction_uuid, payment.amount)
            status_ok = bool(status_result.get('verified'))
            
            if not status_ok:
                logger.warning(f"eSewa server-to-server check failed for {transaction_uuid}. Response: {status_result.get('response')}")

        except Payment.DoesNotExist:
            messages.error(request, 'Payment record not found for verification. Please contact support.')
            logger.error(f"eSewa success callback for non-existent payment_id: {transaction_uuid}")
            return redirect('accounts:booking_history')
        except Exception as e:
            logger.error(f"Error during server-to-server eSewa status query: {e}")
            status_ok = False # Ensure it's false on exception

        # Also verify the signature from the callback data as a secondary check.
        signature_ok = verify_esewa_payment(payment_data)
        if not signature_ok:
            logger.warning(f"eSewa local signature verification failed for {transaction_uuid}.")

        # If signature verifies and status field indicates success, treat as verified
        status_field = str(payment_data.get('status', '')).upper()
        if signature_ok and status_field in ['COMPLETE', 'COMPLETED', 'SUCCESS', 'SUCCESSFUL', 'APPROVED']:
            status_ok = True

        if status_ok or signature_ok:
            with transaction.atomic():
                # We have already fetched the payment object. Proceed with updating the status.
                if not payment:
                     # This case should not be reached if the above logic is sound, but as a safeguard:
                    messages.error(request, 'Could not resolve payment record. Please contact support.')
                    return redirect('accounts:booking_history')

                # Use the associated Booking created earlier during create_booking
                booking = payment.booking

                if payment.payment_status == 'completed':
                    messages.info(request, 'Payment already verified.')
                    return redirect('bookings:booking_confirmation', booking_id=booking.booking_id)

                try:
                    from decimal import Decimal
                    amount_ok = Decimal(str(payment_data.get('total_amount') or payment_data.get('amt'))) == payment.amount
                except Exception:
                    amount_ok = True
                if not amount_ok:
                    messages.error(request, 'Payment amount mismatch detected. Verification failed.')
                    return redirect('accounts:booking_history')

                # Mark seats as unavailable and clear any holds
                for seat in booking.seats.all():
                    seat.is_available = False
                    seat.is_held = False
                    seat.held_by = None
                    seat.held_until = None
                    seat.save()

                # Update booking and payment statuses
                booking.booking_status = 'confirmed'
                booking.payment_status = 'paid'
                booking.save()

                # Persist gateway transaction code if provided and mark payment completed
                gateway_txn_code = (
                    payment_data.get('transaction_code')
                    or payment_data.get('reference_id')
                    or payment_data.get('ref_id')
                    or payment_data.get('transaction_id')
                    or f'ESW{uuid.uuid4().hex[:8].upper()}'
                )
                payment.transaction_id = gateway_txn_code
                payment.payment_status = 'completed'
                payment.save()

                try:
                    send_mail(
                        'TravelMate Booking Confirmation',
                        f'Your booking {booking.booking_id} is confirmed. Transaction: {gateway_txn_code}.',
                        getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@travelmate.local'),
                        [booking.user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.warning(f"Email send failed for booking {booking.booking_id}: {e}")

                # Clean up any stale session data (defensive)
                if 'pending_booking_data' in request.session:
                    try:
                        del request.session['pending_booking_data']
                    except Exception:
                        pass
                if 'pending_payment_id' in request.session:
                    try:
                        del request.session['pending_payment_id']
                    except Exception:
                        pass

                messages.success(request, 'Payment completed successfully via eSewa!')
                return redirect('bookings:booking_confirmation', booking_id=booking.booking_id)
        else:
            # Payment verification failed
            # Release held seats if any
            form_data = request.session.get('pending_booking_data')
            if form_data:
                schedule_id = form_data.get('schedule_id') or form_data.get('bus_schedule')
                selected_seats_str = form_data.get('selected_seats')
                from bookings.models import Seat
                from routes.models import BusSchedule
                schedule = BusSchedule.objects.get(id=schedule_id)
                selected_seat_ids = [int(sid) for sid in selected_seats_str.split(',') if sid.strip().isdigit()]
                selected_seats = Seat.objects.filter(id__in=selected_seat_ids, bus_schedule=schedule)
                for seat in selected_seats:
                    seat.is_held = False
                    seat.held_by = None
                    seat.held_until = None
                    seat.save()
                del request.session['pending_booking_data']
            logger.error(f"eSewa verification failed: data={payment_data}")
            messages.error(request, 'Payment verification failed. Please try again or contact support.')
            # Redirect to payment form with retry flag if we can resolve booking from session
            booking_id_retry = None
            try:
                if 'pending_payment_id' in request.session:
                    from .models import Payment as PaymentModel
                    pay = PaymentModel.objects.get(payment_id=request.session['pending_payment_id'])
                    booking_id_retry = pay.booking.booking_id
            except Exception:
                booking_id_retry = None
            if booking_id_retry:
                return redirect(reverse('payments:payment_form', args=[booking_id_retry]) + '?retry=1')
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
        transaction_uuid = payment_data.get('transaction_uuid') or payment_data.get('oid')
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

    payment = None
    # If this is a retry, we must create a new payment object to avoid duplicate transaction UUIDs.
    if request.GET.get('retry') != '1':
        # If not a retry, try to find an existing payment to resume.
        payment = booking.payments.filter(payment_status__in=['pending', 'failed']).order_by('-updated_at').first()

    if not payment:
        # If no suitable payment exists, or if this is a retry, create a new one.
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

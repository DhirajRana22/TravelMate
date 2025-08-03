from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.conf import settings
from .models import Booking, Seat
from .forms import BookingForm, BookingSearchForm, BookingCancellationForm
from routes.models import BusSchedule
from payments.models import Payment
import qrcode
from io import BytesIO
import uuid
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.core.files.base import ContentFile

@login_required
def seat_selection(request, schedule_id):
    schedule = get_object_or_404(BusSchedule, id=schedule_id, is_active=True)
    
    # Get travel date from request
    travel_date_str = request.GET.get('date')
    if travel_date_str:
        try:
            travel_date = timezone.datetime.strptime(travel_date_str, '%Y-%m-%d').date()
        except ValueError:
            travel_date = timezone.now().date()
    else:
        travel_date = timezone.now().date()
    
    # Check if departure time is in the past (for today's bookings)
    if travel_date == timezone.now().date():
        current_time = timezone.now().time()
        if schedule.departure_time < current_time:
            messages.error(request, 'Cannot book a bus that has already departed.')
            return redirect('routes:route_search')
    elif travel_date < timezone.now().date():
        messages.error(request, 'Cannot book a bus for past dates.')
        return redirect('routes:route_search')
    
    # Get or create seats for this bus schedule
    seats = Seat.objects.filter(bus_schedule=schedule)
    if not seats.exists():
        # Create seats with A/B side pattern: A1, A2, B1, B2, A3, A4, B3, B4, etc.
        a_counter = 1
        b_counter = 1
        
        for i in range(1, schedule.bus.total_seats + 1):
            if i % 4 == 1:  # A side window seat
                seat_number = f"A{a_counter}"
                is_window = True
            elif i % 4 == 2:  # A side aisle seat
                seat_number = f"A{a_counter + 1}"
                is_window = False
                a_counter += 2  # Move to next A row
            elif i % 4 == 3:  # B side aisle seat
                seat_number = f"B{b_counter}"
                is_window = False
            else:  # B side window seat
                seat_number = f"B{b_counter + 1}"
                is_window = True
                b_counter += 2  # Move to next B row
            
            Seat.objects.create(
                bus_schedule=schedule,
                seat_number=seat_number,
                is_window=is_window,
                is_available=True
            )
        
        seats = Seat.objects.filter(bus_schedule=schedule)
    
    # Check seat availability for the specific travel date
    from .models import Booking
    booked_seats = Booking.objects.filter(
        bus_schedule=schedule,
        booking_date=travel_date,
        booking_status__in=['confirmed', 'pending']
    ).values_list('seats__id', flat=True)
    
    # Update seat status based on bookings
    for seat in seats:
        if seat.id in booked_seats:
            seat.status = 'booked'
        else:
            seat.status = 'available'
    
    # Create dynamic seat layout based on actual seat count
    seat_layout = []
    
    # Sort seats by extracting number from seat_number (A1, A2, B1, B2, etc.)
    def seat_sort_key(seat):
        side = seat.seat_number[0]  # A or B
        number = int(seat.seat_number[1:])  # Extract number
        return (number, side)  # Sort by number first, then by side
    
    seats_list = sorted(seats, key=seat_sort_key)
    total_seats = len(seats_list)
    
    # Nepali bus layout: 2x2 rows with aisle + 5-seat last row (standard configuration)
    if total_seats <= 4:
        # Very small buses - single row layout
        for i in range(0, len(seats_list), 4):
            row_seats = seats_list[i:i+4]
            a_seats = [seat for seat in row_seats if seat.seat_number.startswith('A')]
            b_seats = [seat for seat in row_seats if seat.seat_number.startswith('B')]
            
            row = {
                'left_seats': a_seats,
                'right_seats': b_seats
            }
            seat_layout.append(row)
    elif total_seats <= 5:
        # Small buses with 5 seats - single last row
        row = {
            'left_seats': [],
            'right_seats': [],
            'last_row_seats': seats_list
        }
        seat_layout.append(row)
    else:
        # Standard Nepali bus layout: regular 2x2 rows + 5-seat last row
        if total_seats >= 5:
            # Reserve 5 seats for the last row (standard Nepali bus configuration)
            regular_seats_count = total_seats - 5
            
            # Create regular 2x2 rows with aisle
            for i in range(0, regular_seats_count, 4):
                row_seats = seats_list[i:i+4]
                a_seats = [seat for seat in row_seats if seat.seat_number.startswith('A')]
                b_seats = [seat for seat in row_seats if seat.seat_number.startswith('B')]
                
                row = {
                    'left_seats': a_seats,
                    'right_seats': b_seats
                }
                seat_layout.append(row)
            
            # Create the standard 5-seat last row
            last_row_seats = seats_list[regular_seats_count:]
            if last_row_seats:
                row = {
                    'left_seats': [],
                    'right_seats': [],
                    'last_row_seats': last_row_seats
                }
                seat_layout.append(row)
    
    # Handle pre-selected seats from URL (for form validation errors)
    preselected_seat_ids = []
    selected_seats_param = request.GET.get('selected_seats')
    if selected_seats_param:
        try:
            preselected_seat_ids = [int(sid) for sid in selected_seats_param.split(',') if sid.strip().isdigit()]
        except ValueError:
            pass
    
    if request.method == 'POST':
        selected_seat_ids = request.POST.get('selected_seats', '').split(',')
        selected_seat_ids = [sid for sid in selected_seat_ids if sid.strip()]
        
        if not selected_seat_ids:
            messages.error(request, 'Please select at least one seat.')
        else:
            # Redirect to create_booking with selected seats
            seat_ids_str = ','.join(selected_seat_ids)
            return redirect(f"{reverse('bookings:create_booking', args=[schedule_id])}?date={travel_date}&seats={seat_ids_str}")
    
    context = {
        'schedule': schedule,
        'travel_date': travel_date,
        'seat_layout': seat_layout,
        'seats': seats,
        'preselected_seat_ids': preselected_seat_ids,
    }
    
    return render(request, 'bookings/seat_selection.html', context)

@login_required
def quick_booking(request, schedule_id):
    schedule = get_object_or_404(BusSchedule, id=schedule_id, is_active=True)
    
    # Get travel date
    travel_date_str = request.GET.get('date')
    if not travel_date_str:
        messages.error(request, 'Travel date is required.')
        return redirect('routes:route_search')
    
    try:
        travel_date = timezone.datetime.strptime(travel_date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid travel date format.')
        return redirect('routes:route_search')
    
    # Get or create seats for this schedule
    seats = Seat.objects.filter(bus_schedule=schedule)
    if not seats.exists():
        # Auto-create seats if they don't exist
        total_seats = schedule.bus.total_seats
        a_counter = 1
        b_counter = 1
        
        for i in range(total_seats):
            if i % 4 == 0:  # A side window seat
                seat_number = f"A{a_counter}"
                is_window = True
            elif i % 4 == 1:  # A side aisle seat
                seat_number = f"A{a_counter + 1}"
                is_window = False
                a_counter += 2
            elif i % 4 == 2:  # B side aisle seat
                seat_number = f"B{b_counter}"
                is_window = False
            else:  # B side window seat
                seat_number = f"B{b_counter + 1}"
                is_window = True
                b_counter += 2
            
            Seat.objects.create(
                bus_schedule=schedule,
                seat_number=seat_number,
                is_window=is_window,
                is_available=True
            )
        
        seats = Seat.objects.filter(bus_schedule=schedule)
    
    # Check seat availability for the specific travel date
    booked_seats = Booking.objects.filter(
        bus_schedule=schedule,
        booking_date=travel_date,
        booking_status__in=['confirmed', 'pending']
    ).values_list('seats__id', flat=True)
    
    # Update seat status
    for seat in seats:
        if seat.id in booked_seats:
            seat.status = 'booked'
        else:
            seat.status = 'available'
    
    if request.method == 'POST':
        selected_seats_str = request.POST.get('selected_seats')
        passenger_name = request.POST.get('passenger_name')
        passenger_phone = request.POST.get('passenger_phone')
        passenger_email = request.POST.get('passenger_email')
        emergency_contact = request.POST.get('emergency_contact')
        
        if not selected_seats_str:
            messages.error(request, 'Please select at least one seat.')
        elif not passenger_name or not passenger_phone:
            messages.error(request, 'Please fill in all required fields.')
        else:
            try:
                selected_seat_ids = [int(sid.strip()) for sid in selected_seats_str.split(',') if sid.strip()]
                selected_seats = Seat.objects.filter(
                    id__in=selected_seat_ids,
                    bus_schedule=schedule
                )
                
                if len(selected_seats) != len(selected_seat_ids):
                    messages.error(request, 'Some selected seats are no longer available.')
                else:
                    # Calculate total fare
                    subtotal = len(selected_seats) * schedule.base_fare
                    service_fee = round(subtotal * 0.02)
                    total_fare = subtotal + service_fee
                    
                    # Create booking
                    booking = Booking.objects.create(
                        user=request.user,
                        bus_schedule=schedule,
                        booking_date=travel_date,
                        passenger_name=passenger_name,
                        passenger_phone=passenger_phone,
                        passenger_email=passenger_email or '',
                        emergency_contact=emergency_contact or '',
                        total_fare=total_fare,
                        booking_status='confirmed',
                        payment_status='completed'
                    )
                    
                    # Associate seats with booking
                    booking.seats.set(selected_seats)
                    
                    # Generate QR code after seats are associated
                    booking.generate_qr_code()
                    
                    messages.success(request, f'Booking confirmed! Booking ID: {booking.booking_id}')
                    return redirect('bookings:booking_detail', booking_id=booking.booking_id)
                    
            except Exception as e:
                messages.error(request, f'Error creating booking: {str(e)}')
    
    context = {
        'schedule': schedule,
        'travel_date': travel_date,
        'seats': seats.order_by('seat_number'),
    }
    
    return render(request, 'bookings/quick_booking.html', context)

@login_required
def create_booking(request, schedule_id):
    schedule = get_object_or_404(BusSchedule, id=schedule_id, is_active=True)
    
    # Get travel date from request
    travel_date_str = request.GET.get('date')
    if travel_date_str:
        try:
            travel_date = timezone.datetime.strptime(travel_date_str, '%Y-%m-%d').date()
        except ValueError:
            travel_date = timezone.now().date()
    else:
        travel_date = timezone.now().date()
    
    # Get selected seats from request
    seat_ids_str = request.GET.get('seats', '')
    selected_seat_ids = [int(sid) for sid in seat_ids_str.split(',') if sid.strip().isdigit()]
    
    if not selected_seat_ids:
        messages.error(request, 'No seats selected. Please select seats first.')
        return redirect(reverse('bookings:seat_selection', args=[schedule_id]) + f'?date={travel_date}')
    
    # Get selected seats
    selected_seats = Seat.objects.filter(id__in=selected_seat_ids, bus_schedule=schedule)
    
    if len(selected_seats) != len(selected_seat_ids):
        messages.error(request, 'Some selected seats are invalid.')
        return redirect(reverse('bookings:seat_selection', args=[schedule_id]) + f'?date={travel_date}')
    
    # Check if departure time is in the past (for today's bookings)
    if travel_date == timezone.now().date():
        current_time = timezone.now().time()
        if schedule.departure_time < current_time:
            messages.error(request, 'Cannot book a bus that has already departed.')
            return redirect('routes:route_search')
    elif travel_date < timezone.now().date():
        messages.error(request, 'Cannot book a bus for past dates.')
        return redirect('routes:route_search')
    
    # Calculate total fare
    total_fare = schedule.base_fare * len(selected_seats)
    
    if request.method == 'POST':
        print("DEBUG: POST request received")
        print(f"DEBUG: POST data: {request.POST}")
        print(f"DEBUG: POST keys: {list(request.POST.keys())}")
        
        # Get data from POST instead of GET for form submission
        travel_date_str = request.POST.get('travel_date')
        selected_seats_str = request.POST.get('selected_seats', '')
        
        # Parse travel date
        try:
            travel_date = timezone.datetime.strptime(travel_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, 'Invalid travel date.')
            return redirect('routes:route_search')
        
        # Parse selected seats
        selected_seat_ids = [int(sid) for sid in selected_seats_str.split(',') if sid.strip().isdigit()]
        if not selected_seat_ids:
            messages.error(request, 'No seats selected.')
            return redirect(reverse('bookings:seat_selection', args=[schedule_id]) + f'?date={travel_date}')
        
        # Get selected seats
        selected_seats = Seat.objects.filter(id__in=selected_seat_ids, bus_schedule=schedule)
        if len(selected_seats) != len(selected_seat_ids):
            messages.error(request, 'Some selected seats are invalid.')
            return redirect(reverse('bookings:seat_selection', args=[schedule_id]) + f'?date={travel_date}')
        
        # Recalculate total fare
        total_fare = schedule.base_fare * len(selected_seats)
        
        # Map the form data to match BookingForm fields
        form_data = request.POST.copy()
        
        # Use the first passenger's name as the primary passenger name
        if 'passenger_0_name' in form_data:
            form_data['passenger_name'] = form_data['passenger_0_name']
        
        # Use contact_phone as passenger_phone
        if 'contact_phone' in form_data:
            form_data['passenger_phone'] = form_data['contact_phone']
        
        booking_form = BookingForm(form_data)
        print(f"DEBUG: Form created with data: {booking_form.data}")
        print(f"DEBUG: Form fields: {list(booking_form.fields.keys())}")
        print(f"DEBUG: Form is bound: {booking_form.is_bound}")
        
        if booking_form.is_valid():
            print("DEBUG: Form is valid, creating booking")
            
            try:
                with transaction.atomic():
                    # Create booking
                    print("DEBUG: About to create booking object")
                    booking = booking_form.save(commit=False)
                    booking.user = request.user
                    booking.bus_schedule = schedule
                    booking.booking_date = travel_date
                    booking.total_fare = total_fare
                    booking.booking_status = 'confirmed'
                    booking.payment_status = 'pending'
                    booking.save()
                    print(f"DEBUG: Booking created successfully with ID: {booking.booking_id}")
                    
                    # Add selected seats to booking
                    booking.seats.add(*selected_seats)
                    print(f"DEBUG: Added {len(selected_seats)} seats to booking")
                    
                    # Generate QR code after seats are associated
                    booking.generate_qr_code()
                    print("DEBUG: Generated QR code with seat information")
                    
                    # Mark seats as unavailable
                    for seat in selected_seats:
                        seat.is_available = False
                        seat.save()
                    print("DEBUG: Marked seats as unavailable")
                    
                    # Create payment record
                    payment = Payment.objects.create(
                        booking=booking,
                        amount=total_fare,
                        payment_method=booking.payment_method,
                        payment_status='pending'
                    )
                    
                    # Clear localStorage by redirecting with success parameter first
                    # Then redirect to payment page
                    return redirect('payments:process_payment', payment_id=payment.payment_id)
                    
            except Exception as e:
                print(f"DEBUG: Exception occurred during booking creation: {str(e)}")
                print(f"DEBUG: Exception type: {type(e).__name__}")
                import traceback
                print(f"DEBUG: Full traceback: {traceback.format_exc()}")
                messages.error(request, f'Error creating booking: {str(e)}')
                return redirect(reverse('bookings:seat_selection', args=[schedule_id]) + f'?date={travel_date}')
        else:
            print(f"DEBUG: Form is invalid. Errors: {booking_form.errors}")
            messages.error(request, 'Please correct the form errors and try again.')
            # Preserve selected seats when form is invalid
            selected_seats_param = ','.join(str(seat.id) for seat in selected_seats)
            return redirect(reverse('bookings:seat_selection', args=[schedule_id]) + f'?date={travel_date}&selected_seats={selected_seats_param}')
    else:
        booking_form = BookingForm()
    
    context = {
        'schedule': schedule,
        'travel_date': travel_date,
        'selected_seats': selected_seats,
        'total_fare': total_fare,
        'booking_form': booking_form,
    }
    
    return render(request, 'bookings/create_booking.html', context)

@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
    }
    
    return render(request, 'bookings/booking_detail.html', context)

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    # Check if booking can be cancelled
    if booking.booking_status == 'cancelled':
        messages.error(request, 'This booking is already cancelled.')
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    # Check if departure time is within 24 hours
    from datetime import datetime, timedelta
    current_time = timezone.now()
    departure_datetime = datetime.combine(booking.booking_date, booking.bus_schedule.departure_time)
    
    # Make departure_datetime timezone aware
    if timezone.is_naive(departure_datetime):
        departure_datetime = timezone.make_aware(departure_datetime)
    
    if departure_datetime - current_time < timedelta(hours=24):
        messages.error(request, 'Bookings cannot be cancelled within 24 hours of departure.')
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    if request.method == 'POST':
        form = BookingCancellationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Update booking status
                    booking.booking_status = 'cancelled'
                    booking.save()
                    
                    # Make seats available again
                    for seat in booking.seats.all():
                        seat.is_available = True
                        seat.save()
                    
                    # Create refund if payment was made
                    payment = Payment.objects.filter(booking=booking, payment_status='completed').first()
                    if payment:
                        from payments.models import Refund
                        
                        # Calculate refund amount (e.g., 90% of total fare)
                        refund_amount = booking.total_fare * 0.9
                        
                        Refund.objects.create(
                            payment=payment,
                            amount=refund_amount,
                            reason=form.cleaned_data.get('cancellation_reason', 'Customer cancelled booking'),
                            refund_status='pending'
                        )
                    
                    messages.success(request, 'Booking cancelled successfully. If you made a payment, a refund will be processed.')
                    return redirect('accounts:booking_history')
            
            except Exception as e:
                messages.error(request, f'Error cancelling booking: {str(e)}')
                return redirect('bookings:booking_detail', booking_id=booking_id)
    else:
        form = BookingCancellationForm()
    
    context = {
        'booking': booking,
        'form': form,
    }
    
    return render(request, 'bookings/cancel_booking.html', context)

def generate_ticket_pdf(booking):
    """Generate PDF ticket for a booking"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#007bff')
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#333333')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Title
    title = Paragraph("TravelMate Bus Ticket", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Booking Information
    booking_info = [
        ['Booking ID:', booking.booking_id],
        ['Booking Date:', booking.created_at.strftime('%B %d, %Y at %I:%M %p')],
        ['Status:', booking.get_booking_status_display()],
        ['Payment Status:', booking.get_payment_status_display()]
    ]
    
    booking_table = Table(booking_info, colWidths=[2*inch, 3*inch])
    booking_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(Paragraph("Booking Details", header_style))
    elements.append(booking_table)
    elements.append(Spacer(1, 20))
    
    # Journey Information
    journey_info = [
        ['Route:', f"{booking.bus_schedule.route.source.name} → {booking.bus_schedule.route.destination.name}"],
        ['Travel Date:', booking.booking_date.strftime('%B %d, %Y')],
        ['Departure Time:', booking.bus_schedule.departure_time.strftime('%I:%M %p')],
        ['Arrival Time:', booking.bus_schedule.arrival_time.strftime('%I:%M %p')],
        ['Bus:', f"{booking.bus_schedule.bus.bus_name} ({booking.bus_schedule.bus.bus_number})"],
        ['Bus Type:', booking.bus_schedule.bus.bus_type.name]
    ]
    
    journey_table = Table(journey_info, colWidths=[2*inch, 3*inch])
    journey_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(Paragraph("Journey Details", header_style))
    elements.append(journey_table)
    elements.append(Spacer(1, 20))
    
    # Passenger Information
    elements.append(Paragraph("Passenger Details", header_style))
    
    passenger_data = [['Name', 'Phone', 'Seat Numbers']]
    seat_numbers = ', '.join([seat.seat_number for seat in booking.seats.all()])
    passenger_data.append([
        booking.passenger_name,
        booking.passenger_phone,
        seat_numbers
    ])
    
    passenger_table = Table(passenger_data, colWidths=[2*inch, 1.5*inch, 2*inch])
    passenger_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
    ]))
    
    elements.append(passenger_table)
    elements.append(Spacer(1, 20))
    
    # Fare Breakdown
    fare_info = [
        ['Total Amount:', f"रू {booking.total_fare:.2f}"],
        ['Payment Status:', booking.get_payment_status_display()],
        ['Payment Method:', booking.get_payment_method_display() if booking.payment_method else 'Not specified']
    ]
    
    fare_table = Table(fare_info, colWidths=[2*inch, 2*inch])
    fare_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -2), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#007bff')),
        ('TEXTCOLOR', (0, 0), (-1, -2), colors.black),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -2), 'Helvetica'),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(Paragraph("Fare Breakdown", header_style))
    elements.append(fare_table)
    elements.append(Spacer(1, 20))
    
    # QR Code (if available)
    if booking.qr_code:
        try:
            qr_img = Image(booking.qr_code.path, width=1.5*inch, height=1.5*inch)
            qr_data = [['QR Code:', qr_img]]
            qr_table = Table(qr_data, colWidths=[1*inch, 2*inch])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
            ]))
            elements.append(qr_table)
            elements.append(Spacer(1, 20))
        except:
            pass  # Skip QR code if file not found
    
    # Important Notes
    notes_text = """
    <b>Important Instructions:</b><br/>
    • Please arrive at the boarding point at least 15 minutes before departure<br/>
    • Carry a valid government-issued photo ID for verification<br/>
    • Show this ticket (digital or printed) to the bus conductor<br/>
    • Cancellation is allowed up to 2 hours before departure time<br/>
    • Contact customer support for any assistance: +977-1-4567890
    """
    
    notes = Paragraph(notes_text, normal_style)
    elements.append(notes)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@login_required
def download_ticket(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    # Check if booking is confirmed
    if booking.booking_status != 'confirmed':
        messages.error(request, 'Cannot download ticket for unconfirmed or cancelled booking.')
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    # Check if payment is completed
    if booking.payment_status != 'paid':
        messages.error(request, 'Cannot download ticket until payment is completed.')
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    # Generate QR code if not already generated
    if not booking.qr_code:
        booking.generate_qr_code()
    
    # Generate PDF ticket
    pdf_buffer = generate_ticket_pdf(booking)
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{booking.booking_id}.pdf"'
    
    return response

@login_required
def view_ticket(request, booking_id):
    """View ticket in HTML format for preview"""
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    # Check if booking is confirmed
    if booking.booking_status != 'confirmed':
        messages.error(request, 'Cannot view ticket for unconfirmed or cancelled booking.')
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    # Check if payment is completed
    if booking.payment_status != 'paid':
        messages.error(request, 'Cannot view ticket until payment is completed.')
        return redirect('bookings:booking_detail', booking_id=booking_id)
    
    # Generate QR code if not already generated
    if not booking.qr_code:
        booking.generate_qr_code()
    
    # Render ticket template
    context = {
        'booking': booking,
        'qr_code_url': booking.qr_code.url if booking.qr_code else None,
    }
    
    return render(request, 'bookings/ticket.html', context)

def verify_ticket(request, booking_id):
    # This view would be used by bus conductors to verify tickets
    # It could be protected by staff_member_required decorator in production
    
    try:
        booking = Booking.objects.get(booking_id=booking_id)
        
        # Check if booking is valid
        is_valid = (
            booking.booking_status == 'confirmed' and
            booking.payment_status == 'paid' and
            booking.bus_schedule.departure_time.date() == timezone.now().date()
        )
        
        data = {
            'is_valid': is_valid,
            'passenger_name': f"{booking.user.first_name} {booking.user.last_name}",
            'source': booking.bus_schedule.route.source.name,
            'destination': booking.bus_schedule.route.destination.name,
            'departure_time': booking.bus_schedule.departure_time.strftime('%H:%M'),
            'bus_number': booking.bus_schedule.bus.bus_number,
            'seat_numbers': ', '.join([seat.seat_number for seat in booking.seats.all()]),
        }
        
        return JsonResponse(data)
        
    except Booking.DoesNotExist:
        return JsonResponse({'is_valid': False, 'error': 'Booking not found'})

def search_booking(request):
    form = BookingSearchForm(request.GET or None)
    bookings = []
    
    if form.is_valid():
        booking_id = form.cleaned_data.get('booking_id')
        user_email = form.cleaned_data.get('user_email')
        
        if booking_id:
            bookings = Booking.objects.filter(booking_id=booking_id)
        elif user_email:
            from django.contrib.auth.models import User
            users = User.objects.filter(email=user_email)
            if users.exists():
                bookings = Booking.objects.filter(user__in=users)
    
    context = {
        'form': form,
        'bookings': bookings,
    }
    
    return render(request, 'bookings/search_booking.html', context)

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    
    # Check if booking is confirmed and payment is completed
    if booking.booking_status != 'confirmed' or booking.payment_status != 'paid':
        messages.error(request, 'This booking is not confirmed or payment is not completed.')
        return redirect('accounts:booking_history')
    
    # Get payment information
    payment = Payment.objects.filter(booking=booking).first()
    
    context = {
        'booking': booking,
        'payment': payment,
    }
    
    return render(request, 'bookings/booking_confirmation.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg, F, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from bookings.models import Booking
from buses.models import Bus, BusType, BusRecommendation
from routes.models import Route, Location, DynamicBusAssignment, BusSchedule
from payments.models import Payment, Refund
from home.models import PopularDestination, Testimonial
from .forms import (
    DateRangeForm, AdminUserSearchForm, AdminBusSearchForm,
    AdminRouteSearchForm, AdminBookingSearchForm, BusForm, RouteForm, UserForm
)
import json
from datetime import timedelta
import calendar

@staff_member_required
def dashboard_home(request):
    # Get date range from form or use default (last 30 days)
    form = DateRangeForm(request.GET or None)
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    
    # Calculate key metrics
    total_users = User.objects.count()
    new_users = User.objects.filter(date_joined__date__range=[start_date, end_date]).count()
    
    total_bookings = Booking.objects.count()
    recent_bookings = Booking.objects.filter(booking_date__range=[start_date, end_date]).count()
    
    # Revenue only from confirmed bookings with completed payments
    total_revenue = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    recent_revenue = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed',
        payment_date__date__range=[start_date, end_date]
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get booking data for chart
    bookings_by_day = Booking.objects.filter(
        booking_date__range=[start_date, end_date]
    ).annotate(
        day=TruncDay('booking_date')
    ).values('day').annotate(count=Count('id')).order_by('day')
    
    booking_chart_data = {
        'labels': [item['day'].strftime('%Y-%m-%d') for item in bookings_by_day],
        'data': [item['count'] for item in bookings_by_day],
    }
    
    # Get revenue data for chart - only confirmed bookings with completed payments
    revenue_by_day = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed',
        payment_date__date__range=[start_date, end_date]
    ).annotate(
        day=TruncDay('payment_date')
    ).values('day').annotate(total=Sum('amount')).order_by('day')
    
    revenue_chart_data = {
        'labels': [item['day'].strftime('%Y-%m-%d') for item in revenue_by_day],
        'data': [float(item['total']) for item in revenue_by_day],
    }
    
    # Get top routes
    top_routes = Route.objects.annotate(
        booking_count=Count('busschedule__booking')
    ).order_by('-booking_count')[:5]
    
    # Get top buses
    top_buses = Bus.objects.annotate(
        booking_count=Count('busschedule__booking')
    ).order_by('-booking_count')[:5]
    
    # Recent bookings
    recent_booking_list = Booking.objects.order_by('-booking_date')[:10]
    
    # Operational metrics
    active_buses = Bus.objects.filter(is_active=True).count()
    active_routes = Route.objects.filter(is_active=True).count()
    confirmed_bookings = Booking.objects.filter(booking_status='confirmed').count()
    pending_bookings = Booking.objects.filter(booking_status='pending').count()
    
    context = {
        'form': form,
        'total_users': total_users,
        'new_users': new_users,
        'total_bookings': total_bookings,
        'recent_bookings': recent_bookings,
        'total_revenue': total_revenue,
        'recent_revenue': recent_revenue,
        'booking_chart_data': json.dumps(booking_chart_data),
        'revenue_chart_data': json.dumps(revenue_chart_data),
        'top_routes': top_routes,
        'top_buses': top_buses,
        'recent_booking_list': recent_booking_list,
        'active_buses': active_buses,
        'active_routes': active_routes,
        'confirmed_bookings': confirmed_bookings,
        'pending_bookings': pending_bookings,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'dashboard/dashboard_home.html', context)

@staff_member_required
def user_management(request):
    form = AdminUserSearchForm(request.GET or None)
    users = User.objects.all().order_by('-date_joined')
    
    if form.is_valid():
        search_term = form.cleaned_data.get('search')
        if search_term:
            users = users.filter(
                Q(username__icontains=search_term) |
                Q(email__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term)
            )
    
    # Add booking stats to each user
    for user in users:
        user.booking_count = Booking.objects.filter(user=user).count()
        user.total_spent = Payment.objects.filter(
            booking__user=user,
            payment_status='COMPLETED'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'users': users,
        'form': form,
    }
    
    return render(request, 'dashboard/user_management.html', context)

@staff_member_required
def user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Get user's bookings
    bookings = Booking.objects.filter(user=user).order_by('-booking_date')
    
    # Get user's payments
    payments = Payment.objects.filter(booking__user=user).order_by('-payment_date')
    
    # Calculate user stats
    total_bookings = bookings.count()
    completed_bookings = bookings.filter(booking_status='CONFIRMED').count()
    cancelled_bookings = bookings.filter(booking_status='CANCELLED').count()
    total_spent = payments.filter(payment_status='COMPLETED').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get user's favorite routes
    favorite_routes = Route.objects.filter(
        busschedule__booking__user=user
    ).annotate(
        booking_count=Count('busschedule__booking')
    ).order_by('-booking_count')[:5]
    
    context = {
        'user_profile': user,
        'bookings': bookings,
        'payments': payments,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_spent': total_spent,
        'favorite_routes': favorite_routes,
    }
    
    return render(request, 'dashboard/user_detail.html', context)

@staff_member_required
def bus_management(request):
    form = AdminBusSearchForm(request.GET or None)
    buses = Bus.objects.all().select_related('bus_type').order_by('bus_number')
    
    if form.is_valid():
        bus_number = form.cleaned_data.get('bus_number')
        bus_type = form.cleaned_data.get('bus_type')
        capacity_min = form.cleaned_data.get('capacity_min')
        capacity_max = form.cleaned_data.get('capacity_max')
        
        if bus_number:
            buses = buses.filter(bus_number__icontains=bus_number)
        if bus_type:
            buses = buses.filter(bus_type=bus_type)
        if capacity_min is not None:
            buses = buses.filter(capacity__gte=capacity_min)
        if capacity_max is not None:
            buses = buses.filter(capacity__lte=capacity_max)
    
    # Add stats to each bus
    for bus in buses:
        bus.schedule_count = BusSchedule.objects.filter(bus=bus).count()
        bus.total_bookings = Booking.objects.filter(bus_schedule__bus=bus).count()
        bus.total_revenue = Payment.objects.filter(
            booking__bus_schedule__bus=bus,
            payment_status='COMPLETED'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Count active routes (routes with active schedules)
        bus.active_routes_count = Route.objects.filter(
            busschedule__bus=bus,
            is_active=True
        ).distinct().count()
    
    context = {
        'buses': buses,
        'form': form,
        'bus_types': BusType.objects.all(),
    }
    
    return render(request, 'dashboard/bus_management.html', context)

@staff_member_required
def bus_detail(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    
    # Get bus schedules
    schedules = BusSchedule.objects.filter(bus=bus).order_by('departure_time')
    
    # Calculate bus stats
    total_schedules = schedules.count()
    total_bookings = Booking.objects.filter(bus_schedule__bus=bus).count()
    total_revenue = Payment.objects.filter(
        booking__bus_schedule__bus=bus,
        payment_status='COMPLETED'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Add stats to bus object for template access
    bus.total_bookings = total_bookings
    bus.total_revenue = total_revenue
    bus.active_routes_count = Route.objects.filter(
        busschedule__bus=bus,
        is_active=True
    ).distinct().count()
    
    # Get booking data by month
    bookings_by_month = Booking.objects.filter(
        bus_schedule__bus=bus
    ).annotate(
        month=TruncMonth('booking_date')
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    booking_chart_data = {
        'labels': [item['month'].strftime('%b %Y') for item in bookings_by_month],
        'data': [item['count'] for item in bookings_by_month],
    }
    
    context = {
        'bus': bus,
        'schedules': schedules,
        'total_schedules': total_schedules,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'booking_chart_data': json.dumps(booking_chart_data),
    }
    
    return render(request, 'dashboard/bus_detail.html', context)

@staff_member_required
def route_management(request):
    form = AdminRouteSearchForm(request.GET or None)
    routes = Route.objects.all().select_related('source', 'destination').order_by('source__name', 'destination__name')
    
    if form.is_valid():
        source = form.cleaned_data.get('source')
        destination = form.cleaned_data.get('destination')
        distance_min = form.cleaned_data.get('distance_min')
        distance_max = form.cleaned_data.get('distance_max')
        
        if source:
            routes = routes.filter(source__name__icontains=source)
        if destination:
            routes = routes.filter(destination__name__icontains=destination)
        if distance_min is not None:
            routes = routes.filter(distance__gte=distance_min)
        if distance_max is not None:
            routes = routes.filter(distance__lte=distance_max)
    
    # Add stats to each route
    for route in routes:
        route.schedule_count = BusSchedule.objects.filter(route=route).count()
        route.booking_count = Booking.objects.filter(bus_schedule__route=route).count()
        route.revenue = Payment.objects.filter(
            booking__bus_schedule__route=route,
            payment_status='COMPLETED'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'routes': routes,
        'form': form,
        'locations': Location.objects.all(),
    }
    
    return render(request, 'dashboard/route_management.html', context)

@staff_member_required
def route_detail(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    
    # Get route schedules
    schedules = BusSchedule.objects.filter(route=route).order_by('departure_time')
    
    # Calculate route stats
    total_schedules = schedules.count()
    total_bookings = Booking.objects.filter(bus_schedule__route=route).count()
    total_revenue = Payment.objects.filter(
        booking__bus_schedule__route=route,
        payment_status='COMPLETED'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get booking data by month
    bookings_by_month = Booking.objects.filter(
        bus_schedule__route=route
    ).annotate(
        month=TruncMonth('booking_date')
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    booking_chart_data = {
        'labels': [item['month'].strftime('%b %Y') for item in bookings_by_month],
        'data': [item['count'] for item in bookings_by_month],
    }
    
    # Get recent bookings for this route
    recent_bookings = Booking.objects.filter(
        bus_schedule__route=route
    ).select_related('user', 'bus_schedule__bus').prefetch_related('seats').annotate(
        bus_number=F('bus_schedule__bus__bus_number'),
        seats_count=Count('seats'),
        status=F('booking_status')
    ).order_by('-created_at')[:10]
    
    # Add recent_bookings to route object for template access
    route.recent_bookings = recent_bookings
    
    context = {
        'route': route,
        'schedules': schedules,
        'total_schedules': total_schedules,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'booking_chart_data': json.dumps(booking_chart_data),
    }
    
    return render(request, 'dashboard/route_detail.html', context)

@staff_member_required
def route_bus_management(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    
    # Get current bus schedules for this route
    current_schedules = BusSchedule.objects.filter(route=route).select_related('bus')
    assigned_buses = [schedule.bus for schedule in current_schedules]
    
    # Get available buses (not assigned to this route)
    available_buses = Bus.objects.filter(is_active=True).exclude(
        id__in=[bus.id for bus in assigned_buses]
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign_bus':
            bus_id = request.POST.get('bus_id')
            departure_time_str = request.POST.get('departure_time')
            arrival_time_str = request.POST.get('arrival_time')
            base_fare = request.POST.get('base_fare')
            schedule_type = request.POST.get('schedule_type', 'morning')
            buffer_hours = request.POST.get('buffer_hours', 2)
            return_schedule_enabled = request.POST.get('return_schedule_enabled') == 'on'
            effective_from = request.POST.get('effective_from')
            effective_until = request.POST.get('effective_until')
            days_of_week = request.POST.get('days_of_week', '1234567')
            
            if bus_id and departure_time_str and arrival_time_str and base_fare:
                try:
                    from datetime import datetime
                    bus = get_object_or_404(Bus, id=bus_id)
                    
                    # Convert time strings to time objects
                    departure_time = datetime.strptime(departure_time_str, '%H:%M').time()
                    arrival_time = datetime.strptime(arrival_time_str, '%H:%M').time()
                    
                    # Parse dates
                    effective_from_date = None
                    effective_until_date = None
                    
                    if effective_from:
                        effective_from_date = datetime.strptime(effective_from, '%Y-%m-%d').date()
                    
                    if effective_until:
                        effective_until_date = datetime.strptime(effective_until, '%Y-%m-%d').date()
                    
                    # Check if this bus is already assigned to this route with same schedule
                    existing_schedule = BusSchedule.objects.filter(
                        route=route, 
                        bus=bus, 
                        departure_time=departure_time
                    ).first()
                    
                    if not existing_schedule:
                        BusSchedule.objects.create(
                            bus=bus,
                            route=route,
                            departure_time=departure_time,
                            arrival_time=arrival_time,
                            base_fare=base_fare,
                            is_active=True,
                            schedule_type=schedule_type,
                            buffer_hours=int(buffer_hours),
                            return_schedule_enabled=return_schedule_enabled,
                            effective_from=effective_from_date,
                            effective_until=effective_until_date,
                            days_of_week=days_of_week
                        )
                        messages.success(request, f'Bus {bus.bus_number} has been assigned to this route with enhanced scheduling.')
                    else:
                        messages.error(request, f'Bus {bus.bus_number} is already assigned to this route at {departure_time}.')
                except ValueError as e:
                    messages.error(request, f'Invalid date/time format: {str(e)}')
                except Exception as e:
                    messages.error(request, f'Error assigning bus: {str(e)}')
            else:
                messages.error(request, 'Please fill in all required fields.')
                
        elif action == 'remove_bus':
            schedule_id = request.POST.get('schedule_id')
            if schedule_id:
                schedule = get_object_or_404(BusSchedule, id=schedule_id, route=route)
                bus_number = schedule.bus.bus_number
                schedule.delete()
                messages.success(request, f'Bus {bus_number} has been removed from this route.')
        
        elif action == 'update_schedule':
            schedule_id = request.POST.get('schedule_id')
            if schedule_id:
                try:
                    schedule = get_object_or_404(BusSchedule, id=schedule_id, route=route)
                    
                    # Get form data
                    departure_time_str = request.POST.get('departure_time')
                    arrival_time_str = request.POST.get('arrival_time')
                    base_fare = request.POST.get('base_fare')
                    schedule_type = request.POST.get('schedule_type', 'morning')
                    buffer_hours = request.POST.get('buffer_hours', 2)
                    return_schedule_enabled = request.POST.get('return_schedule_enabled') == 'on'
                    effective_from = request.POST.get('effective_from')
                    effective_until = request.POST.get('effective_until')
                    days_of_week = request.POST.get('days_of_week', '1234567')
                    is_active = request.POST.get('is_active') == 'on'
                    
                    # Parse times and dates
                    departure_time = datetime.strptime(departure_time_str, '%H:%M').time()
                    arrival_time = datetime.strptime(arrival_time_str, '%H:%M').time()
                    
                    effective_from_date = None
                    effective_until_date = None
                    
                    if effective_from:
                        effective_from_date = datetime.strptime(effective_from, '%Y-%m-%d').date()
                    
                    if effective_until:
                        effective_until_date = datetime.strptime(effective_until, '%Y-%m-%d').date()
                    
                    # Update schedule
                    schedule.departure_time = departure_time
                    schedule.arrival_time = arrival_time
                    schedule.base_fare = float(base_fare)
                    schedule.schedule_type = schedule_type
                    schedule.buffer_hours = int(buffer_hours)
                    schedule.return_schedule_enabled = return_schedule_enabled
                    schedule.effective_from = effective_from_date
                    schedule.effective_until = effective_until_date
                    schedule.days_of_week = days_of_week
                    schedule.is_active = is_active
                    schedule.save()
                    
                    messages.success(request, f'Schedule for bus {schedule.bus.bus_number} has been updated successfully!')
                except Exception as e:
                    messages.error(request, f'Error updating schedule: {str(e)}')
        
        return redirect('dashboard:route_bus_management', route_id=route_id)
    
    context = {
        'route': route,
        'current_schedules': current_schedules,
        'available_buses': available_buses,
    }
    
    return render(request, 'dashboard/route_bus_management.html', context)

@staff_member_required
def update_schedule(request, schedule_id):
    from routes.models import BusSchedule
    from datetime import datetime
    
    schedule = get_object_or_404(BusSchedule, id=schedule_id)
    route = schedule.route
    
    if request.method == 'POST':
        departure_time_str = request.POST.get('departure_time')
        arrival_time_str = request.POST.get('arrival_time')
        base_fare = request.POST.get('base_fare')
        schedule_type = request.POST.get('schedule_type', 'morning')
        buffer_hours = request.POST.get('buffer_hours', 2)
        return_schedule_enabled = request.POST.get('return_schedule_enabled') == 'on'
        effective_from = request.POST.get('effective_from')
        effective_until = request.POST.get('effective_until')
        days_of_week = request.POST.get('days_of_week', '1234567')
        is_active = request.POST.get('is_active') == 'on'
        
        if departure_time_str and arrival_time_str and base_fare:
            try:
                departure_time = datetime.strptime(departure_time_str, '%H:%M').time()
                arrival_time = datetime.strptime(arrival_time_str, '%H:%M').time()
                
                effective_from_date = None
                effective_until_date = None
                
                if effective_from:
                    effective_from_date = datetime.strptime(effective_from, '%Y-%m-%d').date()
                
                if effective_until:
                    effective_until_date = datetime.strptime(effective_until, '%Y-%m-%d').date()
                
                # Update schedule
                schedule.departure_time = departure_time
                schedule.arrival_time = arrival_time
                schedule.base_fare = float(base_fare)
                schedule.schedule_type = schedule_type
                schedule.buffer_hours = int(buffer_hours)
                schedule.return_schedule_enabled = return_schedule_enabled
                schedule.effective_from = effective_from_date
                schedule.effective_until = effective_until_date
                schedule.days_of_week = days_of_week
                schedule.is_active = is_active
                schedule.save()
                
                messages.success(request, f'Schedule for bus {schedule.bus.bus_number} has been updated successfully!')
                return redirect('dashboard:route_bus_management', route_id=route.id)
            except Exception as e:
                messages.error(request, f'Error updating schedule: {str(e)}')
    
    context = {
        'schedule': schedule,
        'route': route,
    }
    
    return render(request, 'dashboard/update_schedule.html', context)

@staff_member_required
def booking_management(request):
    form = AdminBookingSearchForm(request.GET or None)
    bookings = Booking.objects.all().select_related('user', 'bus_schedule__bus', 'bus_schedule__route').order_by('-booking_date')
    
    if form.is_valid():
        booking_id = form.cleaned_data.get('booking_id')
        user_email = form.cleaned_data.get('user_email')
        booking_status = form.cleaned_data.get('booking_status')
        payment_status = form.cleaned_data.get('payment_status')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        
        if booking_id:
            bookings = bookings.filter(booking_id__icontains=booking_id)
        if user_email:
            bookings = bookings.filter(user__email__icontains=user_email)
        if booking_status:
            bookings = bookings.filter(booking_status=booking_status)
        if payment_status:
            bookings = bookings.filter(payment_status=payment_status)
        if start_date:
            bookings = bookings.filter(booking_date__gte=start_date)
        if end_date:
            bookings = bookings.filter(booking_date__lte=end_date)
    
    context = {
        'bookings': bookings,
        'form': form,
    }
    
    return render(request, 'dashboard/booking_management.html', context)

@staff_member_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Get payment information
    payment = Payment.objects.filter(booking=booking).first()
    refund = None
    if payment:
        refund = Refund.objects.filter(payment=payment).first()
    
    context = {
        'booking': booking,
        'payment': payment,
        'refund': refund,
        'seats': booking.seats.all(),
    }
    
    return render(request, 'dashboard/booking_detail.html', context)

@staff_member_required
def analytics(request):
    # Get date range from form or use default (last 12 months)
    form = DateRangeForm(request.GET or None)
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=365)  # Last 12 months
    
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    
    # Monthly revenue - only from confirmed bookings with completed payments
    revenue_by_month = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed',
        payment_date__date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('payment_date')
    ).values('month').annotate(total=Sum('amount')).order_by('month')
    
    revenue_chart_data = {
        'labels': [item['month'].strftime('%b %Y') for item in revenue_by_month],
        'data': [float(item['total']) for item in revenue_by_month],
    }
    
    # Monthly bookings
    bookings_by_month = Booking.objects.filter(
        booking_date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('booking_date')
    ).values('month').annotate(count=Count('id')).order_by('month')
    
    booking_chart_data = {
        'labels': [item['month'].strftime('%b %Y') for item in bookings_by_month],
        'data': [item['count'] for item in bookings_by_month],
    }
    
    # Booking status distribution
    booking_status_data = Booking.objects.filter(
        booking_date__range=[start_date, end_date]
    ).values('booking_status').annotate(count=Count('id'))
    
    status_chart_data = {
        'labels': [item['booking_status'] for item in booking_status_data],
        'data': [item['count'] for item in booking_status_data],
    }
    
    # Top routes by revenue - only from confirmed bookings with completed payments
    top_routes_revenue = Route.objects.filter(
        busschedule__booking__payments__payment_status='completed',
        busschedule__booking__booking_status='confirmed',
        busschedule__booking__payments__payment_date__range=[start_date, end_date]
    ).annotate(
        revenue=Sum('busschedule__booking__payments__amount')
    ).order_by('-revenue')[:10]
    
    # Top bus types by bookings
    top_bus_types = BusType.objects.filter(
        bus__busschedule__booking__booking_date__range=[start_date, end_date]
    ).annotate(
        booking_count=Count('bus__busschedule__booking')
    ).order_by('-booking_count')[:5]
    
    bus_type_chart_data = {
        'labels': [item.name for item in top_bus_types],
        'data': [item.booking_count for item in top_bus_types],
    }
    
    # Calculate total and recent revenue for display
    total_revenue = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    recent_revenue = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed',
        payment_date__date__range=[start_date, end_date]
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'form': form,
        'revenue_chart_data': json.dumps(revenue_chart_data),
        'booking_chart_data': json.dumps(booking_chart_data),
        'status_chart_data': json.dumps(status_chart_data),
        'bus_type_chart_data': json.dumps(bus_type_chart_data),
        'top_routes_revenue': top_routes_revenue,
        'total_revenue': total_revenue,
        'recent_revenue': recent_revenue,
        'last_updated': timezone.now(),
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'dashboard/analytics.html', context)

@staff_member_required
def recommendation_analytics(request):
    # Get user preferences data
    user_preferences = BusRecommendation.objects.all()
    
    # Calculate average scores by bus type
    bus_type_scores = BusType.objects.annotate(
        avg_score=Avg('bus__busrecommendation__recommendation_score')
    ).filter(avg_score__isnull=False).order_by('-avg_score')
    
    bus_type_chart_data = {
        'labels': [item.name for item in bus_type_scores],
        'data': [float(item.avg_score) for item in bus_type_scores],
    }
    
    # Get most popular amenities
    from buses.models import BusAmenity, UserBusPreference
    
    amenity_preferences = UserBusPreference.objects.values(
        'preferred_amenities'
    ).annotate(count=Count('id'))
    
    amenity_counts = {}
    for pref in amenity_preferences:
        for amenity_id in pref['preferred_amenities']:
            if amenity_id in amenity_counts:
                amenity_counts[amenity_id] += pref['count']
            else:
                amenity_counts[amenity_id] = pref['count']
    
    top_amenities = []
    for amenity_id, count in sorted(amenity_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        try:
            amenity = BusAmenity.objects.get(id=amenity_id)
            top_amenities.append({'name': amenity.name, 'count': count})
        except BusAmenity.DoesNotExist:
            pass
    
    amenity_chart_data = {
        'labels': [item['name'] for item in top_amenities],
        'data': [item['count'] for item in top_amenities],
    }
    
    context = {
        'bus_type_chart_data': json.dumps(bus_type_chart_data),
        'amenity_chart_data': json.dumps(amenity_chart_data),
        'bus_type_scores': bus_type_scores,
        'top_amenities': top_amenities,
    }
    
    return render(request, 'dashboard/recommendation_analytics.html', context)

@staff_member_required
def export_recommendation_data(request):
    """Export recommendation analytics data in various formats"""
    from django.http import HttpResponse
    import csv
    import json
    
    format_type = request.GET.get('format', 'csv')
    
    # Get recommendation data
    recommendations = BusRecommendation.objects.all().select_related('user', 'bus')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="recommendation_data.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['User ID', 'Username', 'Bus ID', 'Bus Name', 'Recommendation Score', 'Created Date'])
        
        for rec in recommendations:
            writer.writerow([
                rec.user.id,
                rec.user.username,
                rec.bus.id,
                rec.bus.bus_name,
                rec.recommendation_score,
                rec.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    
    elif format_type == 'json':
        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="recommendation_data.json"'
        
        data = []
        for rec in recommendations:
            data.append({
                'user_id': rec.user.id,
                'username': rec.user.username,
                'bus_id': rec.bus.id,
                'bus_name': rec.bus.bus_name,
                'recommendation_score': float(rec.recommendation_score),
                'created_date': rec.created_at.isoformat()
            })
        
        response.write(json.dumps(data, indent=2))
        return response
    
    else:
        # Default to CSV if format not recognized
        return redirect('dashboard:recommendation_analytics')

@staff_member_required
def payment_management(request):
    """Admin view for managing payments and refunds"""
    payments = Payment.objects.all().select_related('booking__user', 'booking__bus_schedule__route').order_by('-payment_date')
    
    # Filter by payment status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        payments = payments.filter(payment_status=status_filter)
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        payments = payments.filter(payment_date__date__gte=start_date)
    if end_date:
        payments = payments.filter(payment_date__date__lte=end_date)
    
    # Calculate payment statistics
    total_payments = payments.count()
    completed_payments = payments.filter(payment_status='completed').count()
    pending_payments = payments.filter(payment_status='pending').count()
    failed_payments = payments.filter(payment_status='failed').count()
    
    total_revenue = payments.filter(payment_status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get refunds
    refunds = Refund.objects.all().select_related('payment__booking__user').order_by('-refund_date')
    
    context = {
        'payments': payments,
        'refunds': refunds,
        'total_payments': total_payments,
        'completed_payments': completed_payments,
        'pending_payments': pending_payments,
        'failed_payments': failed_payments,
        'total_revenue': total_revenue,
        'payment_statuses': Payment.PAYMENT_STATUS_CHOICES,
    }
    
    return render(request, 'dashboard/payment_management.html', context)

@staff_member_required
def reports(request):
    """Admin view for generating various reports"""
    # Get date range from form or use default (last 30 days)
    form = DateRangeForm(request.GET or None)
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
    
    # Revenue Report
    revenue_data = Payment.objects.filter(
        payment_status='completed',
        payment_date__date__range=[start_date, end_date]
    ).aggregate(
        total_revenue=Sum('amount'),
        avg_transaction=Avg('amount'),
        transaction_count=Count('id')
    )
    
    # Booking Report
    booking_data = Booking.objects.filter(
        booking_date__range=[start_date, end_date]
    ).aggregate(
        total_bookings=Count('id'),
        confirmed_bookings=Count('id', filter=Q(booking_status='confirmed')),
        cancelled_bookings=Count('id', filter=Q(booking_status='cancelled')),
        pending_bookings=Count('id', filter=Q(booking_status='pending'))
    )
    
    # User Report
    user_data = {
        'total_users': User.objects.count(),
        'new_users': User.objects.filter(date_joined__date__range=[start_date, end_date]).count(),
        'active_users': User.objects.filter(bookings__booking_date__range=[start_date, end_date]).distinct().count()
    }
    
    # Bus Utilization Report
    bus_utilization = Bus.objects.annotate(
        total_bookings=Count('busschedule__booking', filter=Q(busschedule__booking__booking_date__range=[start_date, end_date])),
        total_revenue=Sum('busschedule__booking__payments__amount', filter=Q(
            busschedule__booking__payments__payment_status='completed',
            busschedule__booking__booking_date__range=[start_date, end_date]
        ))
    ).order_by('-total_bookings')[:10]
    
    # Route Performance Report
    route_performance = Route.objects.annotate(
        total_bookings=Count('busschedule__booking', filter=Q(busschedule__booking__booking_date__range=[start_date, end_date])),
        total_revenue=Sum('busschedule__booking__payments__amount', filter=Q(
            busschedule__booking__payments__payment_status='completed',
            busschedule__booking__booking_date__range=[start_date, end_date]
        ))
    ).order_by('-total_revenue')[:10]
    
    context = {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
        'default_start_date': start_date.strftime('%Y-%m-%d'),
        'default_end_date': end_date.strftime('%Y-%m-%d'),
        'revenue_data': revenue_data,
        'booking_data': booking_data,
        'user_data': user_data,
        'bus_utilization': bus_utilization,
        'route_performance': route_performance,
    }
    
    return render(request, 'dashboard/reports.html', context)

# Bus CRUD Views
@staff_member_required
def bus_add(request):
    if request.method == 'POST':
        form = BusForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bus added successfully!')
            return redirect('dashboard:bus_management')
    else:
        form = BusForm()
    
    context = {
        'form': form,
        'title': 'Add New Bus',
        'action': 'Add'
    }
    return render(request, 'dashboard/bus_form.html', context)

@staff_member_required
def bus_edit(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    if request.method == 'POST':
        form = BusForm(request.POST, request.FILES, instance=bus)
        if form.is_valid():
            form.save()
            messages.success(request, 'Bus updated successfully!')
            return redirect('dashboard:bus_detail', bus_id=bus.id)
    else:
        form = BusForm(instance=bus)
    
    context = {
        'form': form,
        'bus': bus,
        'title': 'Edit Bus',
        'action': 'Update'
    }
    return render(request, 'dashboard/bus_form.html', context)

@staff_member_required
def bus_delete(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)
    if request.method == 'POST':
        bus.delete()
        messages.success(request, 'Bus deleted successfully!')
        return redirect('dashboard:bus_management')
    
    context = {
        'bus': bus,
        'title': 'Delete Bus'
    }
    return render(request, 'dashboard/bus_confirm_delete.html', context)

# Route CRUD Views
@staff_member_required
def route_add(request):
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Route added successfully!')
            return redirect('dashboard:route_management')
    else:
        form = RouteForm()
    
    context = {
        'form': form,
        'title': 'Add New Route',
        'action': 'Add'
    }
    return render(request, 'dashboard/route_form.html', context)

@staff_member_required
def route_edit(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    if request.method == 'POST':
        form = RouteForm(request.POST, instance=route)
        if form.is_valid():
            form.save()
            messages.success(request, 'Route updated successfully!')
            return redirect('dashboard:route_detail', route_id=route.id)
    else:
        form = RouteForm(instance=route)
    
    context = {
        'form': form,
        'route': route,
        'title': 'Edit Route',
        'action': 'Update'
    }
    return render(request, 'dashboard/route_form.html', context)

@staff_member_required
def route_delete(request, route_id):
    route = get_object_or_404(Route, id=route_id)
    if request.method == 'POST':
        route.delete()
        messages.success(request, 'Route deleted successfully!')
        return redirect('dashboard:route_management')
    
    context = {
        'route': route,
        'title': 'Delete Route'
    }
    return render(request, 'dashboard/route_confirm_delete.html', context)

# User CRUD Views
@staff_member_required
def user_add(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.password = make_password(password)
            user.save()
            messages.success(request, 'User added successfully!')
            return redirect('dashboard:user_management')
    else:
        form = UserForm()
    
    context = {
        'form': form,
        'title': 'Add New User',
        'action': 'Add'
    }
    return render(request, 'dashboard/user_form.html', context)

@staff_member_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.password = make_password(password)
            user.save()
            messages.success(request, 'User updated successfully!')
            return redirect('dashboard:user_detail', user_id=user.id)
    else:
        form = UserForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'title': 'Edit User',
        'action': 'Update'
    }
    return render(request, 'dashboard/user_form.html', context)

@staff_member_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully!')
        return redirect('dashboard:user_management')
    
    context = {
        'user': user,
        'title': 'Delete User'
    }
    return render(request, 'dashboard/user_confirm_delete.html', context)

# Removed weekly_bus_assignments and intelligent_scheduler_control views

# Removed bus_assignment_analytics view as it's no longer needed

# Removed schedule_management, assignment_management and related CRUD functions

@staff_member_required
def get_real_time_revenue_data(request):
    """API endpoint for real-time revenue data updates"""
    # Get date range from request parameters
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Calculate total revenue from confirmed bookings with completed payments
    total_revenue = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Calculate recent revenue for the specified period
    recent_revenue = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed',
        payment_date__date__range=[start_date, end_date]
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Get daily revenue data for chart
    revenue_by_day = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed',
        payment_date__date__range=[start_date, end_date]
    ).annotate(
        day=TruncDay('payment_date')
    ).values('day').annotate(total=Sum('amount')).order_by('day')
    
    # Format chart data
    chart_data = {
        'labels': [item['day'].strftime('%Y-%m-%d') for item in revenue_by_day],
        'data': [float(item['total']) for item in revenue_by_day],
    }
    
    # Calculate growth percentage
    previous_period_start = start_date - timedelta(days=days)
    previous_revenue = Payment.objects.filter(
        payment_status='completed',
        booking__booking_status='confirmed',
        payment_date__date__range=[previous_period_start, start_date]
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    growth_percentage = 0
    if previous_revenue > 0:
        growth_percentage = ((recent_revenue - previous_revenue) / previous_revenue) * 100
    
    return JsonResponse({
        'total_revenue': float(total_revenue),
        'recent_revenue': float(recent_revenue),
        'chart_data': chart_data,
        'growth_percentage': round(growth_percentage, 2),
        'period_days': days,
        'last_updated': timezone.now().isoformat()
    })

@staff_member_required
def get_schedules_for_route_bus(request):
    """AJAX endpoint to get schedules for a specific route and bus combination"""
    route_id = request.GET.get('route_id')
    bus_id = request.GET.get('bus_id')
    
    if route_id and bus_id:
        schedules = BusSchedule.objects.filter(
            route_id=route_id, bus_id=bus_id, is_active=True
        ).values('id', 'departure_time', 'arrival_time', 'schedule_type')
        
        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                'id': schedule['id'],
                'text': f"{schedule['departure_time'].strftime('%H:%M')} - {schedule['arrival_time'].strftime('%H:%M')} ({schedule['schedule_type'].title()})",
                'departure_time': schedule['departure_time'].strftime('%H:%M'),
                'arrival_time': schedule['arrival_time'].strftime('%H:%M'),
                'schedule_type': schedule['schedule_type']
            })
        
        return JsonResponse({'schedules': schedule_list})
    
    return JsonResponse({'schedules': []})

@staff_member_required
def popular_destinations_management(request):
    """Manage popular destinations"""
    destinations = PopularDestination.objects.all().order_by('display_order')
    
    context = {
        'destinations': destinations,
        'title': 'Popular Destinations Management'
    }
    
    return render(request, 'dashboard/popular_destinations_management.html', context)

@staff_member_required
def popular_destination_add(request):
    """Add new popular destination"""
    if request.method == 'POST':
        location_id = request.POST.get('location')
        title = request.POST.get('title')
        description = request.POST.get('description')
        display_order = request.POST.get('display_order', 0)
        image = request.FILES.get('image')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            location = Location.objects.get(id=location_id)
            destination = PopularDestination.objects.create(
                location=location,
                title=title,
                description=description,
                display_order=int(display_order),
                image=image,
                is_active=is_active
            )
            messages.success(request, f'Popular destination "{title}" added successfully!')
            return redirect('dashboard:popular_destinations_management')
        except Location.DoesNotExist:
            messages.error(request, 'Selected location does not exist.')
        except Exception as e:
            messages.error(request, f'Error adding destination: {str(e)}')
    
    locations = Location.objects.all().order_by('name')
    return render(request, 'dashboard/popular_destination_form.html', {
        'locations': locations,
        'title': 'Add Popular Destination'
    })


# Testimonials Management
@staff_member_required
def testimonials_management(request):
    testimonials = Testimonial.objects.all().order_by('display_order', '-created_at')
    return render(request, 'dashboard/testimonials_management.html', {
        'testimonials': testimonials
    })

@staff_member_required
def testimonial_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        designation = request.POST.get('designation')
        testimonial_text = request.POST.get('testimonial_text')
        rating = request.POST.get('rating')
        display_order = request.POST.get('display_order', 0)
        is_active = request.POST.get('is_active') == 'on'
        avatar = request.FILES.get('avatar')
        
        testimonial = Testimonial.objects.create(
            name=name,
            designation=designation,
            testimonial_text=testimonial_text,
            rating=rating,
            display_order=display_order,
            is_active=is_active,
            avatar=avatar
        )
        
        messages.success(request, f'Testimonial from {testimonial.name} has been added successfully!')
        return redirect('dashboard:testimonials_management')
    
    return render(request, 'dashboard/testimonial_form.html', {
        'title': 'Add New Testimonial',
        'action': 'Add'
    })

@staff_member_required
def testimonial_edit(request, testimonial_id):
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        testimonial.name = request.POST.get('name')
        testimonial.designation = request.POST.get('designation')
        testimonial.testimonial_text = request.POST.get('testimonial_text')
        testimonial.rating = request.POST.get('rating')
        testimonial.display_order = request.POST.get('display_order', 0)
        testimonial.is_active = request.POST.get('is_active') == 'on'
        
        if request.FILES.get('avatar'):
            testimonial.avatar = request.FILES.get('avatar')
        
        testimonial.save()
        
        messages.success(request, f'Testimonial from {testimonial.name} has been updated successfully!')
        return redirect('dashboard:testimonials_management')
    
    return render(request, 'dashboard/testimonial_form.html', {
        'testimonial': testimonial,
        'title': 'Edit Testimonial',
        'action': 'Update'
    })

@staff_member_required
def testimonial_delete(request, testimonial_id):
    testimonial = get_object_or_404(Testimonial, id=testimonial_id)
    
    if request.method == 'POST':
        testimonial_name = testimonial.name
        testimonial.delete()
        messages.success(request, f'Testimonial from {testimonial_name} has been deleted successfully!')
        return redirect('dashboard:testimonials_management')
    
    return render(request, 'dashboard/testimonial_delete.html', {
        'testimonial': testimonial
    })

@staff_member_required
def popular_destination_edit(request, destination_id):
    """Edit popular destination"""
    destination = get_object_or_404(PopularDestination, id=destination_id)
    
    if request.method == 'POST':
        location_id = request.POST.get('location')
        title = request.POST.get('title')
        description = request.POST.get('description')
        display_order = request.POST.get('display_order', 0)
        image = request.FILES.get('image')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            location = Location.objects.get(id=location_id)
            destination.location = location
            destination.title = title
            destination.description = description
            destination.display_order = int(display_order)
            if image:
                destination.image = image
            destination.is_active = is_active
            destination.save()
            
            messages.success(request, f'Popular destination "{title}" updated successfully!')
            return redirect('dashboard:popular_destinations_management')
        except Exception as e:
            messages.error(request, f'Error updating destination: {str(e)}')
    
    locations = Location.objects.all().order_by('name')
    context = {
        'destination': destination,
        'locations': locations,
        'title': 'Edit Popular Destination'
    }
    
    return render(request, 'dashboard/popular_destination_form.html', context)

@staff_member_required
def popular_destination_delete(request, destination_id):
    """Delete popular destination"""
    destination = get_object_or_404(PopularDestination, id=destination_id)
    
    if request.method == 'POST':
        title = destination.title
        destination.delete()
        messages.success(request, f'Popular destination "{title}" deleted successfully!')
        return redirect('dashboard:popular_destinations_management')
    
    context = {
        'destination': destination,
        'title': 'Delete Popular Destination'
    }
    
    return render(request, 'dashboard/popular_destination_confirm_delete.html', context)


# Bus Driver Management Views
@staff_member_required
def driver_management(request):
    """Manage bus drivers"""
    from buses.models import BusDriver
    
    search_query = request.GET.get('search', '')
    drivers = BusDriver.objects.all().select_related('bus').order_by('name')
    
    if search_query:
        drivers = drivers.filter(
            Q(name__icontains=search_query) |
            Q(license_number__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )
    
    # Add statistics
    total_drivers = BusDriver.objects.count()
    assigned_drivers = BusDriver.objects.exclude(bus=None).count()
    unassigned_drivers = BusDriver.objects.filter(bus=None).count()
    
    context = {
        'drivers': drivers,
        'search_query': search_query,
        'total_drivers': total_drivers,
        'assigned_drivers': assigned_drivers,
        'unassigned_drivers': unassigned_drivers,
    }
    
    return render(request, 'dashboard/driver_management.html', context)


@staff_member_required
def driver_add(request):
    """Add a new bus driver"""
    from buses.models import BusDriver, Bus
    
    if request.method == 'POST':
        name = request.POST.get('name')
        license_number = request.POST.get('license_number')
        contact_number = request.POST.get('contact_number')
        experience_years = request.POST.get('experience_years', 0)
        bus_id = request.POST.get('bus')
        
        if name and license_number:
            # Check if license number already exists
            if BusDriver.objects.filter(license_number=license_number).exists():
                messages.error(request, 'A driver with this license number already exists.')
            else:
                driver = BusDriver.objects.create(
                    name=name,
                    license_number=license_number,
                    contact_number=contact_number or '',
                    experience_years=int(experience_years) if experience_years else 0
                )
                
                # Assign to bus if selected
                if bus_id:
                    try:
                        bus = Bus.objects.get(id=bus_id)
                        # Remove current driver from bus
                        BusDriver.objects.filter(bus=bus).update(bus=None)
                        # Assign new driver
                        driver.bus = bus
                        driver.save()
                    except Bus.DoesNotExist:
                        pass
                
                messages.success(request, f'Driver "{name}" added successfully!')
                return redirect('dashboard:driver_management')
        else:
            messages.error(request, 'Name and license number are required.')
    
    # Get available buses (without assigned drivers)
    available_buses = Bus.objects.filter(drivers__isnull=True, is_active=True)
    
    context = {
        'available_buses': available_buses,
    }
    
    return render(request, 'dashboard/driver_form.html', context)


@staff_member_required
def driver_edit(request, driver_id):
    """Edit an existing bus driver"""
    from buses.models import BusDriver, Bus
    
    driver = get_object_or_404(BusDriver, id=driver_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        license_number = request.POST.get('license_number')
        contact_number = request.POST.get('contact_number')
        experience_years = request.POST.get('experience_years', 0)
        bus_id = request.POST.get('bus')
        
        if name and license_number:
            # Check if license number already exists (excluding current driver)
            if BusDriver.objects.filter(license_number=license_number).exclude(id=driver_id).exists():
                messages.error(request, 'A driver with this license number already exists.')
            else:
                driver.name = name
                driver.license_number = license_number
                driver.contact_number = contact_number or ''
                driver.experience_years = int(experience_years) if experience_years else 0
                
                # Handle bus assignment
                if bus_id:
                    try:
                        bus = Bus.objects.get(id=bus_id)
                        # Remove current driver from the selected bus
                        BusDriver.objects.filter(bus=bus).update(bus=None)
                        # Assign this driver to the bus
                        driver.bus = bus
                    except Bus.DoesNotExist:
                        driver.bus = None
                else:
                    driver.bus = None
                
                driver.save()
                messages.success(request, f'Driver "{name}" updated successfully!')
                return redirect('dashboard:driver_management')
        else:
            messages.error(request, 'Name and license number are required.')
    
    # Get available buses (without assigned drivers) plus current bus
    available_buses = Bus.objects.filter(
        Q(drivers__isnull=True) | Q(id=driver.bus.id if driver.bus else None),
        is_active=True
    ).distinct()
    
    context = {
        'driver': driver,
        'available_buses': available_buses,
        'is_edit': True,
    }
    
    return render(request, 'dashboard/driver_form.html', context)


@staff_member_required
def driver_delete(request, driver_id):
    """Delete a bus driver"""
    from buses.models import BusDriver
    
    driver = get_object_or_404(BusDriver, id=driver_id)
    
    if request.method == 'POST':
        name = driver.name
        driver.delete()
        messages.success(request, f'Driver "{name}" deleted successfully!')
        return redirect('dashboard:driver_management')
    
    context = {
        'driver': driver,
    }
    
    return render(request, 'dashboard/driver_confirm_delete.html', context)

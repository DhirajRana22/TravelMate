from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date, time
from .models import Location, Route, BusSchedule
from .forms import RouteSearchForm, LocationForm, RouteForm, BusScheduleForm
from bookings.models import Seat
from buses.models import UserBusPreference
import numpy as np

def route_search(request):
    form = RouteSearchForm(request.GET or None)
    schedules = []
    
    if form.is_valid():
        source_name = form.cleaned_data['source']
        destination_name = form.cleaned_data['destination']
        travel_date = form.cleaned_data['travel_date']
        
        # Convert travel_date to datetime range for the entire day
        from datetime import datetime, time, timedelta
        start_datetime = datetime.combine(travel_date, time.min)
        end_datetime = datetime.combine(travel_date, time.max)
        
        # Find locations by name (case-insensitive search)
        try:
            source_location = Location.objects.get(name__iexact=source_name)
            destination_location = Location.objects.get(name__iexact=destination_name)
            
            # Find routes matching source and destination
            routes = Route.objects.filter(source=source_location, destination=destination_location, is_active=True)
            
            # Find schedules for these routes with proper datetime comparison
            from datetime import datetime
            current_datetime = timezone.now()
            
            schedules = BusSchedule.objects.filter(
                route__in=routes,
                is_active=True
            )
            
            # Filter out schedules that have already departed
            valid_schedules = []
            for schedule in schedules:
                departure_datetime = timezone.make_aware(datetime.combine(travel_date, schedule.departure_time))
                if departure_datetime > current_datetime:
                    valid_schedules.append(schedule)
            
            schedules = valid_schedules
            
            # If searching for past dates, show no results
            if travel_date < timezone.now().date():
                schedules = []
            
            # Sort schedules by departure time
            schedules = sorted(schedules, key=lambda x: x.departure_time)
            
            # Calculate available seats for each schedule on the specific travel date
            for schedule in schedules:
                from bookings.models import Booking
                booked_seats_count = Booking.objects.filter(
                    bus_schedule=schedule,
                    booking_date=travel_date,
                    booking_status='confirmed'
                ).aggregate(
                    total_booked=Count('seats')
                )['total_booked'] or 0
                
                # Calculate available seats
                schedule.available_seats = schedule.bus.total_seats - booked_seats_count
        except Location.DoesNotExist:
            messages.error(request, 'Please enter valid source and destination cities.')
            schedules = []
    else:
        # Handle form validation errors
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    
    # Get popular routes for suggestions
    popular_routes = Route.objects.filter(
        source__is_popular=True, 
        destination__is_popular=True,
        is_active=True
    )[:5]
    
    context = {
        'form': form,
        'schedules': schedules,
        'popular_routes': popular_routes,
        'today': date.today(),
    }
    
    return render(request, 'routes/route_search.html', context)

def route_results(request):
    form = RouteSearchForm(request.GET or None)
    schedules = []
    source = None
    destination = None
    travel_date = None
    
    if form.is_valid():
        source_name = form.cleaned_data['source']
        destination_name = form.cleaned_data['destination']
        travel_date = form.cleaned_data['travel_date']
        
        # Find locations by name (case-insensitive search)
        try:
            source = Location.objects.get(name__iexact=source_name)
            destination = Location.objects.get(name__iexact=destination_name)
            
            # Find routes matching source and destination
            routes = Route.objects.filter(source=source, destination=destination, is_active=True)
            
            # Get dynamic bus assignments for the travel date
            from .models import DynamicBusAssignment
            from datetime import datetime
            current_datetime = timezone.now()
            
            # Get assignments for the travel date
            assignments = DynamicBusAssignment.objects.filter(
                current_route__in=routes,
                departure_date=travel_date,
                is_active=True
            )
            
            # Filter out assignments that have already departed
            valid_assignments = []
            for assignment in assignments:
                departure_datetime = timezone.make_aware(datetime.combine(travel_date, assignment.departure_time))
                if departure_datetime > current_datetime:
                    valid_assignments.append(assignment)
            
            assignments = valid_assignments
            
            # If searching for past dates, show no results
            if travel_date < timezone.now().date():
                assignments = []
            
            # Sort assignments by departure time
            assignments = sorted(assignments, key=lambda x: x.departure_time)
            
            # Convert assignments to schedule-like objects for template compatibility
            schedules = []
            for assignment in assignments:
                # Get the base schedule for fare information
                base_schedule = BusSchedule.objects.filter(
                    route=assignment.current_route,
                    departure_time=assignment.departure_time,
                    is_active=True
                ).first()
                
                if base_schedule:
                    # Create a schedule-like object with assignment data
                    schedule_obj = type('Schedule', (), {
                        'id': base_schedule.id,
                        'bus': assignment.bus,
                        'route': assignment.current_route,
                        'departure_time': assignment.departure_time,
                        'arrival_time': assignment.arrival_time,
                        'journey_duration': base_schedule.journey_duration,
                        'base_fare': base_schedule.base_fare,
                        'is_active': True,
                        'assignment': assignment
                    })()
                    
                    # Calculate available seats for this assignment on the travel date
                    from bookings.models import Booking
                    booked_seats_count = Booking.objects.filter(
                        bus_schedule=base_schedule,
                        booking_date=travel_date,
                        booking_status__in=['confirmed', 'pending']
                    ).aggregate(
                        total_booked=Count('seats')
                    )['total_booked'] or 0
                    
                    from datetime import timedelta
                    departure_datetime = timezone.make_aware(datetime.combine(travel_date, assignment.departure_time))
                    schedule_obj.booking_open = (departure_datetime - current_datetime) >= timedelta(hours=2)
                    schedule_obj.available_seats = assignment.bus.total_seats - booked_seats_count
                    schedules.append(schedule_obj)
            
            # If no dynamic assignments found, fall back to base schedules
            if not schedules:
                base_schedules = BusSchedule.objects.filter(
                    route__in=routes,
                    is_active=True
                )
                if not base_schedules.exists():
                    try:
                        target_route = routes.first()
                        reverse_route = Route.objects.filter(source=destination, destination=source, is_active=True).first()
                        if target_route and reverse_route:
                            forward_schedules = BusSchedule.objects.filter(route=reverse_route, is_active=True)
                            from datetime import time as dtime
                            def to_minutes(t):
                                return int(t.hour) * 60 + int(t.minute)
                            def from_minutes(m):
                                m = m % 1440
                                return dtime(m // 60, m % 60)
                            travel_min_reverse = int(target_route.travel_time.total_seconds() // 60)
                            for fs in forward_schedules:
                                dep_minutes = to_minutes(fs.departure_time)
                                if fs.schedule_type in ['night', 'evening'] or dep_minutes >= 18*60 or dep_minutes < 6*60:
                                    window_start = 18 * 60
                                elif fs.schedule_type == 'morning':
                                    window_start = 6 * 60
                                elif fs.schedule_type == 'afternoon':
                                    window_start = 12 * 60
                                else:
                                    window_start = 18 * 60
                                ret_departure = from_minutes(window_start)
                                ret_arrival = from_minutes(window_start + travel_min_reverse)
                                conflict = BusSchedule.objects.filter(bus=fs.bus, route=target_route, departure_time=ret_departure).exists()
                                if not conflict:
                                    BusSchedule.objects.create(
                                        bus=fs.bus,
                                        route=target_route,
                                        departure_time=ret_departure,
                                        arrival_time=ret_arrival,
                                        base_fare=fs.base_fare,
                                        is_active=True,
                                        schedule_type=fs.schedule_type,
                                        buffer_hours=fs.buffer_hours,
                                        return_schedule_enabled=True,
                                        effective_from=fs.effective_from,
                                        effective_until=fs.effective_until,
                                        days_of_week=fs.days_of_week
                                    )
                            base_schedules = BusSchedule.objects.filter(route__in=routes, is_active=True)
                    except Exception:
                        pass
                
                # Filter schedules that are available on the travel date with proper datetime comparison
                available_schedules = []
                for schedule in base_schedules:
                    if schedule.is_available_on_date(travel_date):
                        departure_datetime = timezone.make_aware(datetime.combine(travel_date, schedule.departure_time))
                        if departure_datetime > current_datetime:
                            available_schedules.append(schedule)
                schedules = sorted(available_schedules, key=lambda x: x.departure_time)
                
                # Calculate available seats for base schedules
                for schedule in schedules:
                    from bookings.models import Booking
                    booked_seats_count = Booking.objects.filter(
                        bus_schedule=schedule,
                        booking_date=travel_date,
                        booking_status='confirmed'
                    ).aggregate(
                        total_booked=Count('seats')
                    )['total_booked'] or 0
                    
                    from datetime import timedelta
                    departure_datetime = timezone.make_aware(datetime.combine(travel_date, schedule.departure_time))
                    schedule.booking_open = (departure_datetime - current_datetime) >= timedelta(hours=2)
                    schedule.available_seats = schedule.bus.total_seats - booked_seats_count
            
            # Apply recommendation sorting if user is authenticated
            if request.user.is_authenticated:
                schedules = sort_schedules_by_preferences(request.user, schedules, travel_date)
            else:
                # Sort by departure time for non-authenticated users
                schedules = sorted(schedules, key=lambda x: x.departure_time)
                    
        except Location.DoesNotExist:
            messages.error(request, 'Please enter valid source and destination cities.')
            schedules = []
            source = None
            destination = None
    else:
        # Handle form validation errors
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
        # Extract raw values from GET parameters for display even if form is invalid
        source = request.GET.get('source', '')
        destination = request.GET.get('destination', '')
        travel_date_str = request.GET.get('travel_date', '')
        try:
            from datetime import datetime
            travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d').date() if travel_date_str else None
        except ValueError:
            travel_date = None
    
    # Get unique bus types for filtering
    from buses.models import BusType
    bus_types = BusType.objects.all()
    
    context = {
        'form': form,
        'schedules': schedules,
        'source': source,
        'destination': destination,
        'travel_date': travel_date,
        'bus_types': bus_types,
    }
    
    return render(request, 'routes/route_results.html', context)

def schedule_detail(request, schedule_id):
    schedule = get_object_or_404(BusSchedule, id=schedule_id, is_active=True)
    
    # Get all seats for this schedule
    seats = Seat.objects.filter(bus_schedule=schedule)
    
    # Calculate available seats
    total_seats = schedule.bus.total_seats
    available_seats = seats.filter(is_available=True).count()
    
    context = {
        'schedule': schedule,
        'total_seats': total_seats,
        'available_seats': available_seats,
        'seats': seats,
    }
    
    return render(request, 'routes/schedule_detail.html', context)

def location_list(request):
    locations = Location.objects.all()
    
    # Search by name or state
    search_query = request.GET.get('search')
    if search_query:
        locations = locations.filter(
            Q(name__icontains=search_query) | 
            Q(state__icontains=search_query) |
            Q(country__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(locations, 10)  # Show 10 locations per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'routes/location_list.html', context)

def route_list(request):
    routes = Route.objects.filter(is_active=True)
    
    # Filter by source or destination
    source = request.GET.get('source')
    destination = request.GET.get('destination')
    
    if source:
        routes = routes.filter(source__name__icontains=source)
    
    if destination:
        routes = routes.filter(destination__name__icontains=destination)
    
    # Search by name
    search_query = request.GET.get('search')
    if search_query:
        routes = routes.filter(
            Q(source__name__icontains=search_query) | 
            Q(destination__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(routes, 10)  # Show 10 routes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'source': source,
        'destination': destination,
    }
    
    return render(request, 'routes/route_list.html', context)


def sort_schedules_by_preferences(user, schedules, travel_date):
    try:
        preference = UserBusPreference.objects.get(user=user)
    except UserBusPreference.DoesNotExist:
        return sorted(schedules, key=lambda x: x.departure_time)

    preferred_types = set(preference.preferred_bus_types.all())
    preferred_amenities = set(preference.preferred_amenities.all())
    max_budget = float(getattr(preference, 'max_budget', 0) or 0)
    price_sens = float(getattr(preference, 'price_sensitivity', 5)) / 10.0
    time_prefs = preference.get_preferred_times_list()

    def time_bin(h):
        if 6 <= h < 12:
            return 'morning'
        if 12 <= h < 18:
            return 'afternoon'
        if 18 <= h < 22:
            return 'evening'
        return 'night'

    def build_vec(s):
        bt = 1.0 if s.bus.bus_type in preferred_types else 0.0
        bus_amen = set(s.bus.amenities.all())
        am = (len(preferred_amenities.intersection(bus_amen)) / len(preferred_amenities)) if preferred_amenities else 0.0
        price = float(s.base_fare)
        pr = 0.0
        if max_budget > 0:
            pr = max(0.0, min(1.0, (max_budget - price) / max_budget))
        dep_h = s.departure_time.hour
        t_pref = 1.0 if time_bin(dep_h) in time_prefs else 0.0
        try:
            total = s.bus.total_seats
            avail = getattr(s, 'available_seats', total)
            ar = max(0.0, min(1.0, (avail / total) if total else 0.0))
        except Exception:
            ar = 0.0
        return np.array([bt, am, pr, t_pref, ar], dtype=float)

    pref_vec = np.array([1.0, 1.0, price_sens, 1.0 if time_prefs else 0.0, 1.0], dtype=float)
    weights = np.array([0.25, 0.15, 0.30, 0.20, 0.10], dtype=float)
    weights = weights / weights.sum()

    def cosine(a, b):
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    scored = []
    for s in schedules:
        v = build_vec(s)
        v_w = v * weights
        p_w = pref_vec * weights
        score = cosine(v_w, p_w) * 100.0
        s.recommendation_score = score
        s.is_recommended = score >= 60.0
        scored.append((s, score))

    scored.sort(key=lambda x: (-x[1], x[0].departure_time))
    return [s for s, _ in scored]

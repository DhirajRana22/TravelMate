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
                # Count booked seats for this schedule on the travel date
                booked_seats_count = Booking.objects.filter(
                    bus_schedule=schedule,
                    booking_date=travel_date,
                    booking_status__in=['confirmed', 'pending']
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
                    
                    schedule_obj.available_seats = assignment.bus.total_seats - booked_seats_count
                    schedules.append(schedule_obj)
            
            # If no dynamic assignments found, fall back to base schedules
            if not schedules:
                base_schedules = BusSchedule.objects.filter(
                    route__in=routes,
                    is_active=True
                )
                
                # Filter schedules that are available on the travel date with proper datetime comparison
                available_schedules = []
                for schedule in base_schedules:
                    if schedule.is_available_on_date(travel_date):
                        # Check if the departure has already passed
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
                    
                    schedule.available_seats = schedule.bus.total_seats - booked_seats_count
            
            # Apply recommendation sorting if user is authenticated
            if request.user.is_authenticated:
                schedules = sort_schedules_by_preferences(request.user, schedules, travel_date)
                    
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
        return redirect('routes:route_search')
    
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
    """Sort schedules based on user preferences, putting recommended buses at the top"""
    try:
        preference = UserBusPreference.objects.get(user=user)
    except UserBusPreference.DoesNotExist:
        # If no preferences, return schedules sorted by departure time
        return sorted(schedules, key=lambda x: x.departure_time)
    
    def calculate_recommendation_score(schedule):
        score = 0
        
        # Bus type preference (40% weight)
        if schedule.bus.bus_type in preference.preferred_bus_types.all():
            score += 40
        
        # Price preference (30% weight)
        if float(schedule.base_fare) <= preference.max_budget:
            # Higher score for lower prices if user is price sensitive
            price_score = (preference.max_budget - float(schedule.base_fare)) / preference.max_budget * 30
            score += price_score * (preference.price_sensitivity / 10)
        
        # Time preference (20% weight)
        departure_hour = schedule.departure_time.hour
        preferred_times = preference.get_preferred_times_list()
        
        for time_pref in preferred_times:
            if time_pref == 'morning' and 6 <= departure_hour < 12:
                score += 20
            elif time_pref == 'afternoon' and 12 <= departure_hour < 18:
                score += 20
            elif time_pref == 'evening' and 18 <= departure_hour < 22:
                score += 20
            elif time_pref == 'night' and (departure_hour >= 22 or departure_hour < 6):
                score += 20
        
        # Amenities preference (10% weight)
        preferred_amenities = set(preference.preferred_amenities.all())
        bus_amenities = set(schedule.bus.amenities.all())
        
        if preferred_amenities:
            amenities_match_ratio = len(preferred_amenities.intersection(bus_amenities)) / len(preferred_amenities)
            score += amenities_match_ratio * 10
        
        return score
    
    # Calculate scores and sort
    schedule_scores = [(schedule, calculate_recommendation_score(schedule)) for schedule in schedules]
    schedule_scores.sort(key=lambda x: (-x[1], x[0].departure_time))  # Sort by score desc, then by time
    
    # Add recommendation score to schedule objects for template use
    sorted_schedules = []
    for schedule, score in schedule_scores:
        schedule.recommendation_score = score
        schedule.is_recommended = score > 30  # Mark as recommended if score > 30
        sorted_schedules.append(schedule)
    
    return sorted_schedules

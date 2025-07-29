from django.shortcuts import render
from django.db.models import Count
from datetime import date
from routes.models import Location, Route
from buses.models import BusType
from routes.forms import RouteSearchForm

def home(request):
    # Get popular destinations
    popular_destinations = Location.objects.annotate(
        route_count=Count('destination_routes')
    ).order_by('-route_count')[:6]
    
    # Get all locations for autocomplete
    all_locations = Location.objects.all().order_by('name')
    
    # Get popular routes
    popular_routes = Route.objects.annotate(
        schedule_count=Count('busschedule')
    ).order_by('-schedule_count')[:5]
    
    # Get bus types for display
    bus_types = BusType.objects.all()[:4]
    
    # Initialize search form
    search_form = RouteSearchForm()
    
    context = {
        'popular_destinations': popular_destinations,
        'all_locations': all_locations,
        'popular_routes': popular_routes,
        'bus_types': bus_types,
        'search_form': search_form,
        'today': date.today(),
    }
    
    return render(request, 'home/index.html', context)

def about(request):
    return render(request, 'home/about.html')

def contact(request):
    return render(request, 'home/contact.html')

def faq(request):
    return render(request, 'home/faq.html')

def terms(request):
    return render(request, 'home/terms.html')

def privacy(request):
    return render(request, 'home/privacy.html')
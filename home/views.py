from django.shortcuts import render
from django.db.models import Count
from datetime import date
from routes.models import Location, Route
from buses.models import BusType
from routes.forms import RouteSearchForm
from .models import PopularDestination, Testimonial

def home(request):
    # Get popular destinations managed by admin
    popular_destinations = PopularDestination.objects.filter(is_active=True).order_by('display_order')[:6]
    
    # Get all locations for autocomplete
    all_locations = Location.objects.all().order_by('name')
    
    # Get popular routes
    popular_routes = Route.objects.annotate(
        schedule_count=Count('busschedule')
    ).order_by('-schedule_count')[:5]
    
    # Get bus types for display
    bus_types = BusType.objects.all()[:4]
    
    # Get testimonials for display
    testimonials = Testimonial.objects.filter(is_active=True).order_by('display_order')[:6]
    
    # Initialize search form
    search_form = RouteSearchForm()
    
    context = {
        'popular_destinations': popular_destinations,
        'all_locations': all_locations,
        'popular_routes': popular_routes,
        'bus_types': bus_types,
        'testimonials': testimonials,
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
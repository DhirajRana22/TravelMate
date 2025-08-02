from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from .models import Bus, BusType, BusAmenity, UserBusPreference, BusRecommendation
from .forms import UserBusPreferenceForm
import numpy as np
from sklearn.neighbors import NearestNeighbors

def bus_list(request):
    buses = Bus.objects.filter(is_active=True)
    
    # Filter by bus type
    bus_type = request.GET.get('type')
    if bus_type:
        buses = buses.filter(bus_type__name__icontains=bus_type)
    
    # Filter by amenities
    amenity = request.GET.get('amenity')
    if amenity:
        buses = buses.filter(amenities__name__icontains=amenity)
    
    # Search by name or number
    search_query = request.GET.get('search')
    if search_query:
        buses = buses.filter(
            Q(bus_name__icontains=search_query) | 
            Q(bus_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(buses, 10)  # Show 10 buses per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all bus types and amenities for filtering
    bus_types = BusType.objects.all()
    amenities = BusAmenity.objects.all()
    
    context = {
        'page_obj': page_obj,
        'bus_types': bus_types,
        'amenities': amenities,
        'search_query': search_query,
        'selected_type': bus_type,
        'selected_amenity': amenity,
    }
    
    return render(request, 'buses/bus_list.html', context)

def bus_detail(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id, is_active=True)
    
    # Get upcoming schedules for this bus
    from routes.models import BusSchedule
    from django.utils import timezone
    
    upcoming_schedules = BusSchedule.objects.filter(
        bus=bus,
        departure_time__gt=timezone.now(),
        is_active=True
    ).order_by('departure_time')[:5]
    
    context = {
        'bus': bus,
        'upcoming_schedules': upcoming_schedules,
    }
    
    return render(request, 'buses/bus_detail.html', context)

@login_required
def bus_preference(request):
    try:
        preference = UserBusPreference.objects.get(user=request.user)
    except UserBusPreference.DoesNotExist:
        preference = None
    
    if request.method == 'POST':
        form = UserBusPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            preference = form.save(commit=False)
            preference.user = request.user
            preference.save()
            form.save_m2m()  # Save many-to-many relationships
            messages.success(request, 'Your bus preferences have been updated successfully!')
            
            # Generate recommendations based on new preferences
            generate_bus_recommendations(request.user)
            
            return redirect('buses:bus_recommendations')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserBusPreferenceForm(instance=preference)
    
    # Get all bus types and amenities for the template
    bus_types = BusType.objects.all()
    amenities = BusAmenity.objects.all()
    
    context = {
        'form': form,
        'bus_types': bus_types,
        'amenities': amenities,
        'preference': preference,
    }
    
    return render(request, 'buses/bus_preference.html', context)

@login_required
def bus_recommendations(request):
    # Get user's recommendations
    recommendations = BusRecommendation.objects.filter(user=request.user)
    
    # If no recommendations exist, generate them
    if not recommendations.exists():
        generate_bus_recommendations(request.user)
        recommendations = BusRecommendation.objects.filter(user=request.user)
    
    context = {
        'recommendations': recommendations,
    }
    
    return render(request, 'buses/bus_recommendations.html', context)

def generate_bus_recommendations(user):
    """Generate bus recommendations for a user using KNN algorithm"""
    try:
        # Get user preferences
        try:
            preference = UserBusPreference.objects.get(user=user)
        except UserBusPreference.DoesNotExist:
            # If user has no preferences, we can't generate recommendations
            return
        
        # Get all active buses
        buses = Bus.objects.filter(is_active=True)
        
        if not buses.exists():
            return
        
        # Create feature vectors for buses
        # Features: bus_type_match, amenities_match_ratio, price_factor, comfort_factor
        bus_features = []
        bus_ids = []
        
        for bus in buses:
            # Bus type match (1 if match, 0 if not)
            bus_type_match = 1 if bus.bus_type == preference.bus_type else 0
            
            # Amenities match ratio (percentage of preferred amenities present in bus)
            preferred_amenities = set(preference.preferred_amenities.all())
            bus_amenities = set(bus.amenities.all())
            
            if preferred_amenities:
                amenities_match_ratio = len(preferred_amenities.intersection(bus_amenities)) / len(preferred_amenities)
            else:
                amenities_match_ratio = 0
            
            # Price factor (inverse of price sensitivity)
            # Higher price sensitivity means lower price factor
            price_factor = (11 - preference.price_sensitivity) / 10
            
            # Comfort factor (direct from comfort preference)
            comfort_factor = preference.comfort_preference / 10
            
            # Create feature vector
            features = [bus_type_match, amenities_match_ratio, price_factor, comfort_factor]
            bus_features.append(features)
            bus_ids.append(bus.id)
        
        # Convert to numpy array
        X = np.array(bus_features)
        
        # Fit KNN model
        # Use min(n_buses, 5) as n_neighbors to handle cases with few buses
        n_neighbors = min(len(buses), 5)
        knn = NearestNeighbors(n_neighbors=n_neighbors, algorithm='auto')
        knn.fit(X)
        
        # Create a query vector based on ideal preferences
        # Ideal: bus_type_match=1, amenities_match_ratio=1, price_factor and comfort_factor from user preferences
        query = np.array([[1, 1, price_factor, comfort_factor]])
        
        # Find nearest neighbors
        distances, indices = knn.kneighbors(query)
        
        # Clear existing recommendations
        BusRecommendation.objects.filter(user=user).delete()
        
        # Create new recommendations
        for i, idx in enumerate(indices[0]):
            bus_id = bus_ids[idx]
            bus = Bus.objects.get(id=bus_id)
            
            # Convert distance to score (inverse relationship)
            # Normalize to 0-100 scale where 100 is best match
            score = 100 * (1 - distances[0][i] / np.max(distances))
            
            BusRecommendation.objects.create(
                user=user,
                bus=bus,
                score=score
            )
            
    except Exception as e:
        # Log the error but don't crash
        print(f"Error generating recommendations: {str(e)}")
        # In production, use proper logging
        # import logging
        # logger = logging.getLogger(__name__)
        # logger.error(f"Error generating recommendations: {str(e)}")

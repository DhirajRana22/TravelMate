from django.contrib import admin
from .models import BusType, BusAmenity, Bus, BusDriver, UserBusPreference, BusRecommendation
from .forms import BusAmenityForm

@admin.register(BusType)
class BusTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(BusAmenity)
class BusAmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'description')
    search_fields = ('name',)
    form = BusAmenityForm

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('bus_number', 'bus_name', 'bus_type', 'total_seats', 'is_active')
    list_filter = ('bus_type', 'is_active', 'created_at')
    search_fields = ('bus_number', 'bus_name')
    filter_horizontal = ('amenities',)

@admin.register(BusDriver)
class BusDriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'license_number', 'contact_number', 'experience_years', 'bus', 'is_active')
    list_filter = ('is_active', 'experience_years')
    search_fields = ('name', 'license_number', 'contact_number')

@admin.register(UserBusPreference)
class UserBusPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'bus_type', 'price_sensitivity', 'comfort_preference', 'created_at')
    list_filter = ('bus_type', 'price_sensitivity', 'comfort_preference')
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('preferred_amenities',)

@admin.register(BusRecommendation)
class BusRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'bus', 'score', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'bus__bus_name', 'bus__bus_number')

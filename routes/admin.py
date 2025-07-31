from django.contrib import admin
from .models import Location, Route, BusSchedule, DynamicBusAssignment

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'country', 'is_popular')
    list_filter = ('is_popular', 'country', 'state')
    search_fields = ('name', 'state')

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('source', 'destination', 'distance', 'travel_time', 'is_active')
    list_filter = ('is_active', 'source__is_popular', 'destination__is_popular')
    search_fields = ('source__name', 'destination__name')

@admin.register(BusSchedule)
class BusScheduleAdmin(admin.ModelAdmin):
    list_display = ('bus', 'route', 'departure_time', 'arrival_time', 'base_fare', 'is_active')
    list_filter = ('is_active', 'bus', 'route')
    search_fields = ('bus__bus_name', 'route__source__name', 'route__destination__name')
    ordering = ('departure_time',)

@admin.register(DynamicBusAssignment)
class DynamicBusAssignmentAdmin(admin.ModelAdmin):
    list_display = ('bus', 'current_route', 'departure_date', 'departure_time', 'arrival_date', 'arrival_time', 'next_available_date', 'is_active')
    list_filter = ('is_active', 'departure_date', 'current_route__source', 'current_route__destination', 'bus__bus_type')
    search_fields = ('bus__bus_name', 'bus__bus_number', 'current_route__source__name', 'current_route__destination__name')
    date_hierarchy = 'departure_date'
    readonly_fields = ('next_available_date', 'next_available_time')
    
    fieldsets = (
        ('Assignment Details', {
            'fields': ('bus', 'current_route', 'is_active')
        }),
        ('Schedule Information', {
            'fields': ('departure_date', 'departure_time', 'arrival_date', 'arrival_time')
        }),
        ('Availability', {
            'fields': ('next_available_date', 'next_available_time'),
            'classes': ('collapse',)
        }),
    )

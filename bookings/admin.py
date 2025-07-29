from django.contrib import admin
from .models import Seat, Booking

@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('bus_schedule', 'seat_number', 'is_available')
    list_filter = ('is_available', 'bus_schedule__bus__bus_type')
    search_fields = ('bus_schedule__bus__bus_number', 'seat_number')

class SeatInline(admin.TabularInline):
    model = Booking.seats.through
    extra = 0
    verbose_name = 'Booked Seat'
    verbose_name_plural = 'Booked Seats'
    readonly_fields = ('seat',)
    can_delete = False

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'user', 'bus_schedule', 'booking_date', 'total_fare', 'booking_status', 'payment_status')
    list_filter = ('booking_status', 'payment_status', 'booking_date', 'payment_method')
    search_fields = ('booking_id', 'user__username', 'user__email', 'bus_schedule__bus__bus_number')
    readonly_fields = ('booking_id', 'qr_code', 'created_at', 'updated_at')
    date_hierarchy = 'booking_date'
    inlines = [SeatInline]
    exclude = ('seats',)
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('booking_id', 'user', 'bus_schedule', 'booking_date')
        }),
        ('Payment Information', {
            'fields': ('total_fare', 'payment_status', 'payment_method')
        }),
        ('Status Information', {
            'fields': ('booking_status',)
        }),
        ('QR Code', {
            'fields': ('qr_code',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('user', 'bus_schedule', 'booking_date')
        return self.readonly_fields

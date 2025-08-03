from django.db import models
from django.contrib.auth.models import User
from routes.models import BusSchedule
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

class Seat(models.Model):
    bus_schedule = models.ForeignKey(BusSchedule, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_available = models.BooleanField(default=True)
    is_window = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.bus_schedule.bus.bus_name} - {self.seat_number}"
    
    class Meta:
        unique_together = ('bus_schedule', 'seat_number')

class Booking(models.Model):
    BOOKING_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    )
    
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('esewa', 'eSewa'),
        ('khalti', 'Khalti'),
        ('bus_conductor', 'Pay to Bus Conductor'),
    )
    
    booking_id = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    bus_schedule = models.ForeignKey(BusSchedule, on_delete=models.CASCADE)
    seats = models.ManyToManyField(Seat, related_name='bookings')
    booking_date = models.DateField()
    passenger_name = models.CharField(max_length=100)
    passenger_phone = models.CharField(max_length=15)
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    booking_status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    qr_code = models.ImageField(upload_to='qr_codes', blank=True, null=True)
    
    def __str__(self):
        return f"Booking {self.booking_id} - {self.user.username}"
    
    def generate_qr_code(self):
        """Generate QR code for the booking with complete information"""
        if self.booking_status == 'confirmed':
            # Get seat numbers
            seat_numbers = ', '.join([str(seat.seat_number) for seat in self.seats.all()])
            
            # Create comprehensive QR code data
            qr_data = f"""Booking ID: {self.booking_id}
User: {self.user.username}
Date: {self.booking_date}
Bus: {self.bus_schedule.bus.bus_name}
Route: {self.bus_schedule.route}
Total Passengers: {self.seats.count()}
Seat No.: {seat_numbers}
Travel Date: {self.booking_date}"""
            
            qr = qrcode.QRCode(
                version=2,  # Increased version to accommodate more data
                error_correction=qrcode.constants.ERROR_CORRECT_M,  # Better error correction
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            self.qr_code.save(f"{self.booking_id}.png", File(buffer), save=False)
            self.save(update_fields=['qr_code'])

    def save(self, *args, **kwargs):
        # Generate unique booking_id if not set
        if not self.booking_id:
            import uuid
            while True:
                booking_id = f'BK{uuid.uuid4().hex[:8].upper()}'
                if not Booking.objects.filter(booking_id=booking_id).exists():
                    self.booking_id = booking_id
                    break
        
        super().save(*args, **kwargs)

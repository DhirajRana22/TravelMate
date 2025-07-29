from django.db import models
from datetime import timedelta
from django.core.validators import MinValueValidator
from buses.models import Bus

class Location(models.Model):
    name = models.CharField(max_length=100)
    state = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=50, default='Nepal')
    is_popular = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Route(models.Model):
    source = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='source_routes')
    destination = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='destination_routes')
    distance = models.PositiveIntegerField(help_text='Distance in kilometers')
    travel_time = models.DurationField(default=timedelta(hours=1), help_text='Estimated travel time for this route')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.source.name} to {self.destination.name}"
    
    class Meta:
        unique_together = ('source', 'destination')

class BusSchedule(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    journey_duration = models.DurationField(blank=True, null=True)  # Calculated field
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    # New fields for dynamic scheduling
    effective_from = models.DateField(help_text='Date from which this schedule is effective')
    effective_until = models.DateField(blank=True, null=True, help_text='Date until which this schedule is effective')
    days_of_week = models.CharField(max_length=7, default='1234567', help_text='Days of week (1=Monday, 7=Sunday)')
    
    def __str__(self):
        return f"{self.bus.bus_name} - {self.route} - {self.departure_time}"
    
    def is_available_on_date(self, date):
        """Check if this schedule is available on a specific date"""
        # Check if date is within effective range
        if date < self.effective_from:
            return False
        if self.effective_until and date > self.effective_until:
            return False
        
        # Check if day of week is included
        weekday = str(date.weekday() + 1)  # Convert to 1-7 format
        return weekday in self.days_of_week
    
    def save(self, *args, **kwargs):
        # Calculate journey duration
        if self.departure_time and self.arrival_time:
            from datetime import datetime, timedelta
            departure = datetime.combine(datetime.today(), self.departure_time)
            arrival = datetime.combine(datetime.today(), self.arrival_time)
            
            # Handle overnight journeys
            if arrival < departure:
                arrival += timedelta(days=1)
                
            self.journey_duration = arrival - departure
            
        super().save(*args, **kwargs)

class DynamicBusAssignment(models.Model):
    """Model to track dynamic bus assignments based on travel duration"""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    current_route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='current_assignments')
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_date = models.DateField()
    arrival_time = models.TimeField()
    next_available_date = models.DateField(help_text='Date when bus becomes available for next assignment')
    next_available_time = models.TimeField(help_text='Time when bus becomes available for next assignment')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.bus.bus_name} - {self.current_route} - {self.departure_date}"
    
    class Meta:
        unique_together = ('bus', 'departure_date', 'departure_time')

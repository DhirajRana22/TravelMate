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
    """Enhanced bus schedule model for comprehensive scheduling functionality"""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Enhanced scheduling fields
    effective_from = models.DateField(auto_now_add=True, help_text='Date from which this schedule is effective')
    effective_until = models.DateField(null=True, blank=True, help_text='Date until which this schedule is effective')
    days_of_week = models.CharField(max_length=7, default='1234567', help_text='Days of week (1=Monday, 7=Sunday)')
    schedule_type = models.CharField(max_length=20, choices=[
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ('night', 'Night'),
    ], default='morning')
    buffer_hours = models.PositiveIntegerField(default=2, help_text='Buffer time in hours between trips')
    return_schedule_enabled = models.BooleanField(default=False, help_text='Enable automatic return journey scheduling')
    
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.bus.bus_name} - {self.route} - {self.departure_time}"
    
    def is_available_on_date(self, travel_date):
        """Check if this schedule is available on the given date"""
        # Check if the date is within the effective period
        if travel_date < self.effective_from:
            return False
        
        if self.effective_until and travel_date > self.effective_until:
            return False
        
        # Check if the day of week is included (1=Monday, 7=Sunday)
        day_of_week = str(travel_date.weekday() + 1)  # Convert to 1-7 format
        if day_of_week not in self.days_of_week:
            return False
        
        return self.is_active
    
    @property
    def journey_duration(self):
        """Calculate journey duration from departure to arrival time"""
        from datetime import datetime, timedelta
        
        # Create datetime objects for calculation
        departure_dt = datetime.combine(datetime.today().date(), self.departure_time)
        arrival_dt = datetime.combine(datetime.today().date(), self.arrival_time)
        
        # Handle overnight journeys
        if arrival_dt < departure_dt:
            arrival_dt += timedelta(days=1)
        
        duration = arrival_dt - departure_dt
        
        # Format duration as hours and minutes
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"
    
    class Meta:
        unique_together = ('bus', 'route', 'departure_time')
        ordering = ['departure_time']

# Removed WeeklyBusAssignment model as it's no longer needed

class DynamicBusAssignment(models.Model):
    """Enhanced model to track intelligent bus assignments based on travel duration"""
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    current_route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='current_assignments')
    departure_date = models.DateField()
    departure_time = models.TimeField()
    arrival_date = models.DateField()
    arrival_time = models.TimeField()
    next_available_date = models.DateField(help_text='Date when bus becomes available for next assignment')
    next_available_time = models.TimeField(help_text='Time when bus becomes available for next assignment')
    # Enhanced fields for intelligent scheduling
    return_route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='return_assignments', null=True, blank=True)
    return_departure_date = models.DateField(null=True, blank=True)
    return_departure_time = models.TimeField(null=True, blank=True)
    assignment_type = models.CharField(max_length=20, choices=[
        ('primary', 'Primary Journey'),
        ('return', 'Return Journey'),
        ('alternate', 'Alternate Day Assignment'),
    ], default='primary')
    # Removed weekly_assignment field as WeeklyBusAssignment model no longer exists
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.bus.bus_name} - {self.current_route} - {self.departure_date} ({self.assignment_type})"
    
    def get_travel_duration_hours(self):
        """Calculate travel duration in hours"""
        from datetime import datetime, timedelta
        departure_datetime = datetime.combine(self.departure_date, self.departure_time)
        arrival_datetime = datetime.combine(self.arrival_date, self.arrival_time)
        
        # Handle overnight journeys
        if arrival_datetime < departure_datetime:
            arrival_datetime += timedelta(days=1)
            
        duration = arrival_datetime - departure_datetime
        return duration.total_seconds() / 3600
    
    def determine_next_schedule_type(self):
        """Determine the appropriate schedule type for next assignment based on arrival time"""
        arrival_hour = self.arrival_time.hour
        
        if 6 <= arrival_hour < 12:
            return 'afternoon'  # Arrived in morning, can do afternoon
        elif 12 <= arrival_hour < 18:
            return 'evening'    # Arrived in afternoon, can do evening
        elif 18 <= arrival_hour < 24:
            return 'morning'    # Arrived in evening, next day morning
        else:  # 0 <= arrival_hour < 6
            return 'morning'    # Arrived at night, same day morning
    
    class Meta:
        unique_together = ('bus', 'departure_date', 'departure_time')
        ordering = ['-departure_date', '-departure_time']

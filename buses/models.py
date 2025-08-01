from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User

class BusType(models.Model):
    name = models.CharField(max_length=50)  # Normal, AC/Deluxe, Sleeper, etc.
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class BusAmenity(models.Model):
    name = models.CharField(max_length=50)  # WiFi, Charging Port, Meal, etc.
    icon = models.CharField(max_length=50, blank=True, null=True)  # For frontend display
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name

class Bus(models.Model):
    bus_number = models.CharField(max_length=20, unique=True)
    bus_name = models.CharField(max_length=100)
    bus_type = models.ForeignKey(BusType, on_delete=models.CASCADE)
    total_seats = models.PositiveIntegerField()
    amenities = models.ManyToManyField(BusAmenity, blank=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='bus_images', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.bus_name} ({self.bus_number})"

class BusDriver(models.Model):
    name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    contact_number = models.CharField(max_length=15)
    experience_years = models.PositiveIntegerField(default=0)
    bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, blank=True, related_name='drivers')
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class UserBusPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bus_preferences')
    bus_type = models.ForeignKey(BusType, on_delete=models.CASCADE)
    preferred_amenities = models.ManyToManyField(BusAmenity, blank=True)
    price_sensitivity = models.IntegerField(default=5, help_text='1-10 scale, 10 being most sensitive to price')
    comfort_preference = models.IntegerField(default=5, help_text='1-10 scale, 10 being highest comfort preference')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Bus Preferences"

class BusRecommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bus_recommendations')
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    score = models.FloatField(help_text='Recommendation score based on KNN algorithm')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Recommendation for {self.user.username}: {self.bus.bus_name} (Score: {self.score})"
    
    class Meta:
        ordering = ['-score']
        unique_together = ('user', 'bus')

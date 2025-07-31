from django.db import models
from routes.models import Location

class PopularDestination(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    title = models.CharField(max_length=200, help_text="Display title for the destination")
    description = models.TextField(blank=True, help_text="Brief description of the destination")
    image = models.ImageField(upload_to='destinations/', help_text="Upload an attractive image for this destination")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which to display (lower numbers first)")
    is_active = models.BooleanField(default=True, help_text="Whether to show this destination on the homepage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', 'title']
        verbose_name = 'Popular Destination'
        verbose_name_plural = 'Popular Destinations'
    
    def __str__(self):
        return f"{self.title} ({self.location.name})"
    
    @property
    def route_count(self):
        """Get the number of routes available for this destination"""
        return self.location.destination_routes.count() + self.location.source_routes.count()


class Testimonial(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    name = models.CharField(max_length=100, help_text="Customer's name")
    designation = models.CharField(max_length=100, help_text="Customer's designation or role (e.g., Regular Traveler, Business Traveler)")
    testimonial_text = models.TextField(help_text="The testimonial content")
    rating = models.PositiveIntegerField(choices=RATING_CHOICES, default=5, help_text="Rating out of 5 stars")
    avatar = models.ImageField(upload_to='testimonials/', blank=True, null=True, help_text="Customer's profile picture (optional)")
    display_order = models.PositiveIntegerField(default=0, help_text="Order in which to display (lower numbers first)")
    is_active = models.BooleanField(default=True, help_text="Whether to show this testimonial on the homepage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'
    
    def __str__(self):
        return f"{self.name} - {self.rating} stars"
    
    def get_star_range(self):
        """Returns a range for displaying full stars"""
        return range(self.rating)
    
    def get_empty_star_range(self):
        """Returns a range for displaying empty stars"""
        return range(5 - self.rating)
from django import forms
from django.db import models
from django.contrib.auth.models import User
from accounts.models import Profile
from buses.models import Bus, BusType, BusAmenity, BusDriver
from routes.models import Location, Route, DynamicBusAssignment
from bookings.models import Booking
from payments.models import Payment, Refund

__all__ = [
    'DateRangeForm', 'AdminUserSearchForm', 'AdminBusSearchForm', 'AdminRouteSearchForm', 
    'AdminBookingSearchForm', 'BusForm', 'RouteForm', 'UserForm'
]

class DateRangeForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")
        
        return cleaned_data



class AdminUserSearchForm(forms.Form):
    username = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    is_active = forms.BooleanField(required=False, initial=True)

class AdminBusSearchForm(forms.Form):
    bus_number = forms.CharField(max_length=20, required=False)
    bus_name = forms.CharField(max_length=100, required=False)
    bus_type = forms.ModelChoiceField(queryset=BusType.objects.all(), required=False, empty_label="All Types")
    is_active = forms.BooleanField(required=False, initial=True)

class AdminRouteSearchForm(forms.Form):
    source = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, empty_label="All Sources")
    destination = forms.ModelChoiceField(queryset=Location.objects.all(), required=False, empty_label="All Destinations")
    is_active = forms.BooleanField(required=False, initial=True)

class AdminBookingSearchForm(forms.Form):
    booking_id = forms.CharField(max_length=20, required=False)
    user_email = forms.EmailField(required=False)
    booking_status = forms.ChoiceField(choices=[(None, 'All Statuses')] + list(Booking.BOOKING_STATUS_CHOICES), required=False)
    payment_status = forms.ChoiceField(choices=[(None, 'All Statuses')] + list(Booking.PAYMENT_STATUS_CHOICES), required=False)
    date_range = forms.ChoiceField(choices=[
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('last_7_days', 'Last 7 Days'),
        ('last_30_days', 'Last 30 Days'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('custom', 'Custom Range'),
    ], required=False, initial='today')
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

class BusForm(forms.ModelForm):
    bus_type_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter bus type (e.g., AC Deluxe, Sleeper)'
        }),
        help_text="Enter the type of bus (will be created if it doesn't exist)"
    )
    amenities_list = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amenities separated by commas (e.g., WiFi, AC, Charging Port)'
        }),
        help_text="Enter amenities separated by commas (will be created if they don't exist)"
    )
    driver_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter driver name'
        }),
        help_text='Enter the name of the bus driver'
    )
    driver_license = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter license number'
        }),
        help_text='Enter driver license number'
    )
    driver_contact = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter contact number'
        }),
        help_text='Enter driver contact number'
    )
    
    class Meta:
        model = Bus
        fields = ['bus_number', 'bus_name', 'total_seats', 'image', 'is_active']
        widgets = {
            'bus_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bus_name': forms.TextInput(attrs={'class': 'form-control'}),
            'total_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing existing bus, populate bus type, amenities, and driver fields
        if self.instance and self.instance.pk:
            if self.instance.bus_type:
                self.fields['bus_type_name'].initial = self.instance.bus_type.name
            
            # Populate amenities list
            amenities_names = [amenity.name for amenity in self.instance.amenities.all()]
            self.fields['amenities_list'].initial = ', '.join(amenities_names)
            
            current_driver = self.instance.drivers.filter(is_active=True).first()
            if current_driver:
                self.fields['driver_name'].initial = current_driver.name
                self.fields['driver_license'].initial = current_driver.license_number
                self.fields['driver_contact'].initial = current_driver.contact_number
    
    def save(self, commit=True):
        bus = super().save(commit=False)
        
        # Handle bus type creation/update
        bus_type_name = self.cleaned_data.get('bus_type_name')
        if bus_type_name:
            bus_type, created = BusType.objects.get_or_create(
                name=bus_type_name,
                defaults={'description': f'Bus type: {bus_type_name}'}
            )
            bus.bus_type = bus_type
        
        if commit:
            bus.save()
            self.save_m2m()
            
            # Handle amenities creation/update
            amenities_list = self.cleaned_data.get('amenities_list')
            if amenities_list:
                # Clear existing amenities
                bus.amenities.clear()
                
                # Parse comma-separated amenities
                amenity_names = [name.strip() for name in amenities_list.split(',') if name.strip()]
                
                for amenity_name in amenity_names:
                    amenity, created = BusAmenity.objects.get_or_create(
                        name=amenity_name,
                        defaults={'description': f'Bus amenity: {amenity_name}'}
                    )
                    bus.amenities.add(amenity)
        
        driver_name = self.cleaned_data.get('driver_name')
        driver_license = self.cleaned_data.get('driver_license')
        driver_contact = self.cleaned_data.get('driver_contact')
        
        if commit and driver_name:
            # Remove current driver assignment
            BusDriver.objects.filter(bus=bus).update(bus=None)
            
            # Create or update driver for this bus
            if driver_license:
                driver, created = BusDriver.objects.get_or_create(
                    license_number=driver_license,
                    defaults={
                        'name': driver_name,
                        'contact_number': driver_contact or '',
                        'bus': bus
                    }
                )
                if not created:
                    driver.name = driver_name
                    driver.contact_number = driver_contact or ''
                    driver.bus = bus
                    driver.save()
            else:
                # Create driver without license number (temporary)
                BusDriver.objects.create(
                    name=driver_name,
                    license_number=f"TEMP_{bus.bus_number}_{driver_name[:5]}",
                    contact_number=driver_contact or '',
                    bus=bus
                )
        
        return bus

class RouteForm(forms.ModelForm):
    source_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter source location name'
        }),
        help_text='Enter the name of the source location'
    )
    destination_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter destination location name'
        }),
        help_text='Enter the name of the destination location'
    )
    
    travel_time_hours = forms.IntegerField(
        min_value=0,
        max_value=23,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Hours',
            'min': '0',
            'max': '23'
        }),
        help_text='Travel time in hours (0-23)'
    )
    travel_time_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minutes',
            'min': '0',
            'max': '59'
        }),
        help_text='Travel time in minutes (0-59)'
    )
    
    class Meta:
        model = Route
        fields = ['distance', 'is_active']
        widgets = {
            'distance': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # If editing existing route, populate the text fields
            self.fields['source_name'].initial = self.instance.source.name
            self.fields['destination_name'].initial = self.instance.destination.name
            
            # Populate travel time fields if editing
            if self.instance.travel_time:
                total_seconds = int(self.instance.travel_time.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                self.fields['travel_time_hours'].initial = hours
                self.fields['travel_time_minutes'].initial = minutes
    
    def clean(self):
        cleaned_data = super().clean()
        source_name = cleaned_data.get('source_name')
        destination_name = cleaned_data.get('destination_name')
        travel_time_hours = cleaned_data.get('travel_time_hours')
        travel_time_minutes = cleaned_data.get('travel_time_minutes')
        
        if source_name and destination_name:
            if source_name.lower() == destination_name.lower():
                raise forms.ValidationError("Source and destination cannot be the same.")
        
        # Validate travel time
        if travel_time_hours is not None and travel_time_minutes is not None:
            if travel_time_hours == 0 and travel_time_minutes == 0:
                raise forms.ValidationError("Travel time must be greater than 0.")
        
        return cleaned_data
    
    def save(self, commit=True):
        from datetime import timedelta
        
        route = super().save(commit=False)
        
        # Get or create source location
        source_name = self.cleaned_data['source_name']
        source_location, created = Location.objects.get_or_create(
            name__iexact=source_name,
            defaults={'name': source_name.title()}
        )
        route.source = source_location
        
        # Get or create destination location
        destination_name = self.cleaned_data['destination_name']
        destination_location, created = Location.objects.get_or_create(
            name__iexact=destination_name,
            defaults={'name': destination_name.title()}
        )
        route.destination = destination_location
        
        # Set travel time
        travel_time_hours = self.cleaned_data.get('travel_time_hours', 0)
        travel_time_minutes = self.cleaned_data.get('travel_time_minutes', 0)
        route.travel_time = timedelta(hours=travel_time_hours, minutes=travel_time_minutes)
        
        if commit:
            route.save()
        return route

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and password != confirm_password:
            raise forms.ValidationError("Passwords don't match.")
        
        return cleaned_data
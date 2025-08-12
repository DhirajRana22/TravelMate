from django import forms
from django.utils import timezone
from .models import Location, Route, BusSchedule

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'state', 'country', 'is_popular']

class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['source', 'destination', 'distance', 'is_active']
        widgets = {
            'distance': forms.NumberInput(attrs={'min': 0}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        destination = cleaned_data.get('destination')
        
        if source and destination and source == destination:
            raise forms.ValidationError("Source and destination cannot be the same.")
        
        return cleaned_data

class BusScheduleForm(forms.ModelForm):
    class Meta:
        model = BusSchedule
        fields = ['bus', 'route', 'departure_time', 'arrival_time', 'base_fare', 'is_active']
        widgets = {
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'arrival_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'base_fare': forms.NumberInput(attrs={'min': 0}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        departure_time = cleaned_data.get('departure_time')
        arrival_time = cleaned_data.get('arrival_time')
        
        if departure_time and arrival_time and departure_time >= arrival_time:
            raise forms.ValidationError("Departure time must be before arrival time.")
        
        return cleaned_data

class RouteSearchForm(forms.Form):
    source = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control custom-input',
            'placeholder': 'Enter source city',
            'list': 'source-list',
            'autocomplete': 'off'
        })
    )
    destination = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control custom-input',
            'placeholder': 'Enter destination city',
            'list': 'destination-list',
            'autocomplete': 'off'
        })
    )
    travel_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def clean_travel_date(self):
        travel_date = self.cleaned_data.get('travel_date')
        if travel_date:
            today = timezone.now().date()
            if travel_date < today:
                raise forms.ValidationError("Travel date cannot be in the past.")
        return travel_date
    
    def clean(self):
        cleaned_data = super().clean()
        source = cleaned_data.get('source')
        destination = cleaned_data.get('destination')
        
        if source and destination and source == destination:
            raise forms.ValidationError("Source and destination cannot be the same.")
        
        return cleaned_data
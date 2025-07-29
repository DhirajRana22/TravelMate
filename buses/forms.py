from django import forms
from .models import Bus, BusType, BusAmenity, BusDriver, UserBusPreference

class BusForm(forms.ModelForm):
    class Meta:
        model = Bus
        fields = ['bus_number', 'bus_name', 'bus_type', 'total_seats', 'amenities', 'description', 'image', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class BusTypeForm(forms.ModelForm):
    class Meta:
        model = BusType
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class BusAmenityForm(forms.ModelForm):
    class Meta:
        model = BusAmenity
        fields = ['name', 'icon', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class BusDriverForm(forms.ModelForm):
    class Meta:
        model = BusDriver
        fields = ['name', 'license_number', 'contact_number', 'experience_years', 'bus', 'is_active']

class UserBusPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserBusPreference
        fields = ['bus_type', 'preferred_amenities', 'price_sensitivity', 'comfort_preference']
        widgets = {
            'price_sensitivity': forms.NumberInput(attrs={'min': 1, 'max': 10}),
            'comfort_preference': forms.NumberInput(attrs={'min': 1, 'max': 10}),
        }
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

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            return name
        # Case-insensitive uniqueness check
        qs = BusAmenity.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('An amenity with this name already exists (case-insensitive).')
        return name

class BusDriverForm(forms.ModelForm):
    class Meta:
        model = BusDriver
        fields = ['name', 'license_number', 'contact_number', 'experience_years', 'bus', 'is_active']

class UserBusPreferenceForm(forms.ModelForm):
    preferred_times = forms.MultipleChoiceField(
        choices=UserBusPreference.TIME_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    class Meta:
        model = UserBusPreference
        fields = [
            'preferred_bus_types', 'preferred_amenities', 
            'price_sensitivity', 'comfort_preference', 'max_budget', 
            'preferred_times', 'preferred_seat_position'
        ]
        widgets = {
            'price_sensitivity': forms.NumberInput(attrs={'min': 1, 'max': 10}),
            'comfort_preference': forms.NumberInput(attrs={'min': 1, 'max': 10}),
            'preferred_bus_types': forms.CheckboxSelectMultiple(),
            'preferred_amenities': forms.CheckboxSelectMultiple(),
            'max_budget': forms.NumberInput(attrs={'min': 100, 'max': 10000, 'step': 100}),
            'preferred_seat_position': forms.Select(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Set initial values for preferred_times from the stored string
            self.fields['preferred_times'].initial = self.instance.get_preferred_times_list()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            # Handle preferred_times separately
            preferred_times = self.cleaned_data.get('preferred_times', [])
            instance.set_preferred_times_list(preferred_times)
            instance.save()
        return instance
from django import forms
from .models import Booking, Seat
from routes.models import BusSchedule

class SeatSelectionForm(forms.Form):
    def __init__(self, bus_schedule, *args, **kwargs):
        super(SeatSelectionForm, self).__init__(*args, **kwargs)
        self.bus_schedule = bus_schedule
        
        # Get all available seats for this bus schedule
        available_seats = Seat.objects.filter(bus_schedule=bus_schedule, is_available=True)
        
        # Create a multiple choice field for seat selection
        self.fields['selected_seats'] = forms.ModelMultipleChoiceField(
            queryset=available_seats,
            widget=forms.CheckboxSelectMultiple,
            required=True
        )
    
    def clean_selected_seats(self):
        selected_seats = self.cleaned_data.get('selected_seats')
        
        if not selected_seats or len(selected_seats) == 0:
            raise forms.ValidationError("Please select at least one seat.")
        
        # Check if any of the selected seats are no longer available
        unavailable_seats = [seat for seat in selected_seats if not seat.is_available]
        if unavailable_seats:
            seat_numbers = ', '.join([seat.seat_number for seat in unavailable_seats])
            raise forms.ValidationError(f"The following seats are no longer available: {seat_numbers}")
        
        return selected_seats

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['passenger_name', 'passenger_phone', 'payment_method']
        widgets = {
            'passenger_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter passenger name'}),
            'passenger_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'passenger_name': 'Passenger Name',
            'passenger_phone': 'Phone Number',
            'payment_method': 'Payment Method',
        }

class BookingSearchForm(forms.Form):
    booking_id = forms.CharField(max_length=20, required=False)
    user_email = forms.EmailField(required=False)
    
    def clean(self):
        cleaned_data = super().clean()
        booking_id = cleaned_data.get('booking_id')
        user_email = cleaned_data.get('user_email')
        
        if not booking_id and not user_email:
            raise forms.ValidationError("Please provide either a booking ID or user email.")
        
        return cleaned_data

class BookingCancellationForm(forms.Form):
    confirm_cancellation = forms.BooleanField(
        required=True,
        label="I understand that cancellation may be subject to cancellation fees based on the booking policy."
    )
    cancellation_reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )
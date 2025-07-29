from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile
import re

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=True, help_text='Enter your phone number')
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Remove any non-digit characters
        phone_number = re.sub(r'\D', '', phone_number)
        
        # Validate phone number length (exactly 10 digits)
        if len(phone_number) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        
        # Check if phone number already exists
        if Profile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        
        return phone_number
    
    def save(self, commit=True):
        user = super(UserRegistrationForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Generate username from first and last name
        base_username = f"{self.cleaned_data['first_name'].lower()}{self.cleaned_data['last_name'].lower()}"
        base_username = re.sub(r'[^a-zA-Z0-9]', '', base_username)  # Remove special characters
        
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user.username = username
        
        if commit:
            user.save()
            # Save phone number to profile
            user.profile.phone_number = self.cleaned_data['phone_number']
            user.profile.save()
        
        return user

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email or Phone Number'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    
    error_messages = {
        'invalid_login': 'Please enter a correct email/phone and password. Note that both fields may be case-sensitive.',
        'inactive': 'This account is inactive.',
    }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone_number', 'address', 'profile_picture', 'date_of_birth')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
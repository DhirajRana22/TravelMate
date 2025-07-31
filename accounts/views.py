from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import UserRegistrationForm, UserLoginForm, ProfileUpdateForm, UserUpdateForm
from .models import Profile

def register(request):
    if request.user.is_authenticated:
        # Redirect based on user role
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:dashboard_home')
        else:
            return redirect('home:home')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Profile is created via signals
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('accounts:login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        # Redirect based on user role
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:dashboard_home')
        else:
            return redirect('home:home')
    
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Role-based redirection after login
                if user.is_staff or user.is_superuser:
                    next_url = request.GET.get('next', 'dashboard:dashboard_home')
                    messages.success(request, f'Welcome to Admin Dashboard, {username}!')
                else:
                    next_url = request.GET.get('next', 'home:home')
                    messages.success(request, f'Welcome back, {username}!')
                
                return redirect(next_url)
        else:
            messages.error(request, 'Please enter a correct email/phone and password. Note that both fields may be case-sensitive.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home:home')

@login_required
def profile(request):
    # Import here to avoid circular imports
    from bookings.models import Booking
    from payments.models import Payment
    
    # Get user statistics
    recent_bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')[:5]
    total_bookings = Booking.objects.filter(user=request.user).count()
    
    # Calculate total spent
    total_spent = 0
    payments = Payment.objects.filter(booking__user=request.user, payment_status='completed')
    for payment in payments:
        total_spent += payment.amount
    
    # Get favorite route (most booked route)
    favorite_route = None
    if total_bookings > 0:
        from django.db.models import Count
        route_counts = Booking.objects.filter(user=request.user).values('bus_schedule__route__source', 'bus_schedule__route__destination').annotate(count=Count('id')).order_by('-count').first()
        if route_counts:
            favorite_route = f"{route_counts['bus_schedule__route__source']} to {route_counts['bus_schedule__route__destination']}"
    
    context = {
        'recent_bookings': recent_bookings,
        'total_bookings': total_bookings,
        'total_spent': total_spent,
        'favorite_route': favorite_route,
    }
    
    return render(request, 'accounts/profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    
    return render(request, 'accounts/edit_profile.html', context)

@login_required
def change_password(request):
    # Django's built-in password change form
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update the session with the new password hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def booking_history(request):
    # Import here to avoid circular imports
    from bookings.models import Booking
    
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    return render(request, 'accounts/booking_history.html', {'bookings': bookings})

@login_required
def payment_history(request):
    # Import here to avoid circular imports
    from payments.models import Payment
    
    payments = Payment.objects.filter(booking__user=request.user).order_by('-payment_date')
    return render(request, 'accounts/payment_history.html', {'payments': payments})

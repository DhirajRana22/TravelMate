from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class EmailPhoneBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with email or phone number
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find user by email or phone number
            user = User.objects.get(
                Q(email=username) | Q(profile__phone_number=username)
            )
            
            # Check if the password is correct
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
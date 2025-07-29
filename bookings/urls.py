from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('quick/<int:schedule_id>/', views.quick_booking, name='quick_booking'),
    path('seats/<int:schedule_id>/', views.seat_selection, name='seat_selection'),
    path('create/<int:schedule_id>/', views.create_booking, name='create_booking'),
    path('detail/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('cancel/<str:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('ticket/<str:booking_id>/', views.view_ticket, name='view_ticket'),
    path('ticket/<str:booking_id>/download/', views.download_ticket, name='download_ticket'),
    path('verify/<str:booking_id>/', views.verify_ticket, name='verify_ticket'),
    path('search/', views.search_booking, name='search_booking'),
    path('confirmation/<str:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
]
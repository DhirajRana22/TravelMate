from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('users/', views.user_management, name='user_management'),
    path('users/', views.user_management, name='admin_users'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('buses/', views.bus_management, name='bus_management'),
    path('buses/', views.bus_management, name='admin_buses'),
    path('buses/add/', views.bus_add, name='bus_add'),
    path('buses/<int:bus_id>/', views.bus_detail, name='bus_detail'),
    path('buses/<int:bus_id>/edit/', views.bus_edit, name='bus_edit'),
    path('buses/<int:bus_id>/delete/', views.bus_delete, name='bus_delete'),
    path('buses/<int:bus_id>/status/', views.bus_status_update, name='bus_status_update'),
    path('routes/', views.route_management, name='route_management'),
    path('routes/', views.route_management, name='admin_routes'),
    path('routes/add/', views.route_add, name='route_add'),
    path('routes/<int:route_id>/', views.route_detail, name='route_detail'),
    path('routes/<int:route_id>/edit/', views.route_edit, name='route_edit'),
    path('routes/<int:route_id>/delete/', views.route_delete, name='route_delete'),
    path('routes/<int:route_id>/buses/', views.route_bus_management, name='route_bus_management'),
    path('schedules/<int:schedule_id>/update/', views.update_schedule, name='update_schedule'),
    path('bookings/', views.booking_management, name='booking_management'),
    path('bookings/', views.booking_management, name='admin_bookings'),
    path('bookings/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<str:booking_id>/confirm/', views.booking_confirm, name='booking_confirm'),
    path('bookings/<str:booking_id>/cancel/', views.booking_cancel, name='booking_cancel'),
    path('bookings/<str:booking_id>/refund/', views.booking_refund, name='booking_refund'),
    path('bookings/<str:booking_id>/payment-reminder/', views.booking_payment_reminder, name='booking_payment_reminder'),
    path('bookings/<str:booking_id>/send-ticket/', views.booking_send_ticket, name='booking_send_ticket'),
    path('bookings/<str:booking_id>/notify/', views.booking_notify, name='booking_notify'),
    path('payments/', views.payment_management, name='admin_payments'),
    path('reports/', views.reports, name='admin_reports'),
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/recommendations/', views.recommendation_analytics, name='recommendation_analytics'),
    path('analytics/recommendations/export/', views.export_recommendation_data, name='export_recommendation_data'),
    # Removed weekly assignments, scheduler control, and schedule management features
    # AJAX endpoints
    path('api/schedules-for-route-bus/', views.get_schedules_for_route_bus, name='get_schedules_for_route_bus'),
    path('api/real-time-revenue/', views.get_real_time_revenue_data, name='get_real_time_revenue_data'),
    # Popular Destinations Management
    path('destinations/', views.popular_destinations_management, name='popular_destinations_management'),
    path('destinations/add/', views.popular_destination_add, name='popular_destination_add'),
    path('destinations/<int:destination_id>/edit/', views.popular_destination_edit, name='popular_destination_edit'),
    path('destinations/<int:destination_id>/delete/', views.popular_destination_delete, name='popular_destination_delete'),
    
    # Testimonials Management
    path('testimonials/', views.testimonials_management, name='testimonials_management'),
    path('testimonials/add/', views.testimonial_add, name='testimonial_add'),
    path('testimonials/<int:testimonial_id>/edit/', views.testimonial_edit, name='testimonial_edit'),
    path('testimonials/<int:testimonial_id>/delete/', views.testimonial_delete, name='testimonial_delete'),
    
    # Bus Driver Management
    path('drivers/', views.driver_management, name='driver_management'),
    path('drivers/add/', views.driver_add, name='driver_add'),
    path('drivers/<int:driver_id>/edit/', views.driver_edit, name='driver_edit'),
    path('drivers/<int:driver_id>/delete/', views.driver_delete, name='driver_delete'),
]
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
    path('routes/', views.route_management, name='route_management'),
    path('routes/', views.route_management, name='admin_routes'),
    path('routes/add/', views.route_add, name='route_add'),
    path('routes/<int:route_id>/', views.route_detail, name='route_detail'),
    path('routes/<int:route_id>/edit/', views.route_edit, name='route_edit'),
    path('routes/<int:route_id>/delete/', views.route_delete, name='route_delete'),
    path('routes/<int:route_id>/buses/', views.route_bus_management, name='route_bus_management'),
    path('bookings/', views.booking_management, name='booking_management'),
    path('bookings/', views.booking_management, name='admin_bookings'),
    path('bookings/<str:booking_id>/', views.booking_detail, name='booking_detail'),
    path('payments/', views.payment_management, name='admin_payments'),
    path('reports/', views.reports, name='admin_reports'),
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/recommendations/', views.recommendation_analytics, name='recommendation_analytics'),
    path('analytics/recommendations/export/', views.export_recommendation_data, name='export_recommendation_data'),
]
from django.urls import path
from . import views

app_name = 'routes'

urlpatterns = [
    path('search/', views.route_search, name='route_search'),
    path('results/', views.route_results, name='route_results'),
    path('schedule/<int:schedule_id>/', views.schedule_detail, name='schedule_detail'),
    path('locations/', views.location_list, name='location_list'),
    path('list/', views.route_list, name='route_list'),
]
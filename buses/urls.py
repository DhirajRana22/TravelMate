from django.urls import path
from . import views

app_name = 'buses'

urlpatterns = [
    path('', views.bus_list, name='bus_list'),
    path('<int:bus_id>/', views.bus_detail, name='bus_detail'),
    path('preferences/', views.bus_preference, name='bus_preference'),
    path('recommendations/', views.bus_recommendations, name='bus_recommendations'),
]
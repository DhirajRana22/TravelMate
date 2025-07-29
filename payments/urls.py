from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('process/<uuid:payment_id>/', views.process_payment, name='process_payment'),
    path('success/<uuid:payment_id>/', views.payment_success, name='payment_success'),
    path('history/', views.payment_history, name='payment_history'),
    path('detail/<uuid:payment_id>/', views.payment_detail, name='payment_detail'),
    path('refund/request/<uuid:payment_id>/', views.request_refund, name='request_refund'),
    path('verify/', views.verify_payment, name='verify_payment'),
    
    # Admin URLs
    path('admin/refunds/', views.admin_refund_list, name='admin_refund_list'),
    path('admin/refunds/process/<int:refund_id>/', views.admin_process_refund, name='admin_process_refund'),
]
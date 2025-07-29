from django.contrib import admin
from .models import Payment, Refund

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'booking', 'amount', 'payment_method', 'payment_status', 'payment_date')
    list_filter = ('payment_status', 'payment_method', 'payment_date')
    search_fields = ('payment_id', 'booking__booking_id', 'transaction_id', 'booking__user__username')
    readonly_fields = ('payment_id', 'payment_date', 'updated_at')
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_id', 'booking', 'amount')
        }),
        ('Transaction Information', {
            'fields': ('payment_method', 'payment_status', 'transaction_id')
        }),
        ('Timestamps', {
            'fields': ('payment_date', 'updated_at')
        }),
    )

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('payment', 'amount', 'refund_status', 'refund_date', 'processed_date')
    list_filter = ('refund_status', 'refund_date', 'processed_date')
    search_fields = ('payment__payment_id', 'payment__booking__booking_id', 'payment__booking__user__username')
    readonly_fields = ('refund_date',)
    date_hierarchy = 'refund_date'
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('payment', 'amount', 'reason')
        }),
        ('Status Information', {
            'fields': ('refund_status', 'refund_date', 'processed_date')
        }),
    )

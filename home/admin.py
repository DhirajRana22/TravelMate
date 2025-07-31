from django.contrib import admin
from .models import PopularDestination, Testimonial

@admin.register(PopularDestination)
class PopularDestinationAdmin(admin.ModelAdmin):
    list_display = ['title', 'location', 'display_order', 'is_active', 'route_count', 'created_at']
    list_filter = ['is_active', 'location', 'created_at']
    search_fields = ['title', 'location__name', 'description']
    list_editable = ['display_order', 'is_active']
    ordering = ['display_order', 'title']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('location', 'title', 'description')
        }),
        ('Display Settings', {
            'fields': ('image', 'display_order', 'is_active')
        }),
    )
    
    def route_count(self, obj):
        return obj.route_count
    route_count.short_description = 'Available Routes'
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'designation', 'rating', 'is_active', 'display_order', 'created_at']
    list_filter = ['rating', 'is_active', 'created_at']
    search_fields = ['name', 'designation', 'testimonial_text']
    list_editable = ['is_active', 'display_order']
    ordering = ['display_order', '-created_at']
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('name', 'designation', 'avatar')
        }),
        ('Testimonial Content', {
            'fields': ('testimonial_text', 'rating')
        }),
        ('Display Settings', {
            'fields': ('display_order', 'is_active')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request)
    
    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }
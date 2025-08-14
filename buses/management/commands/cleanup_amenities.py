from django.core.management.base import BaseCommand
from buses.models import BusAmenity, Bus, UserBusPreference

class Command(BaseCommand):
    help = 'Clean up duplicate amenities and standardize naming'
    
    def handle(self, *args, **options):
        # Define mapping of duplicates to the canonical version
        duplicate_mappings = {
            'Wi-Fi': 'WiFi',
            'AC': 'Air Conditioning', 
            'TV': 'Entertainment',
            'Music': 'Music System',
            'Water': 'Water Bottle',
            'Charger': 'Charging Port',
        }
        
        # Remove amenities that don't belong (bus types)
        invalid_amenities = ['Normal Deluxe', 'Semi Sleeper']
        
        self.stdout.write('Starting amenity cleanup...')
        
        # Remove invalid amenities
        for invalid_name in invalid_amenities:
            try:
                invalid_amenity = BusAmenity.objects.get(name=invalid_name)
                # Remove from buses first
                for bus in Bus.objects.filter(amenities=invalid_amenity):
                    bus.amenities.remove(invalid_amenity)
                    self.stdout.write(f'Removed "{invalid_name}" from bus: {bus.bus_name}')
                
                invalid_amenity.delete()
                self.stdout.write(f'Deleted invalid amenity: {invalid_name}')
            except BusAmenity.DoesNotExist:
                pass
        
        # Handle duplicates
        for duplicate_name, canonical_name in duplicate_mappings.items():
            try:
                duplicate_amenity = BusAmenity.objects.get(name=duplicate_name)
                canonical_amenity = BusAmenity.objects.get(name=canonical_name)
                
                # Move all buses from duplicate to canonical
                for bus in Bus.objects.filter(amenities=duplicate_amenity):
                    bus.amenities.remove(duplicate_amenity)
                    bus.amenities.add(canonical_amenity)
                    self.stdout.write(f'Updated bus "{bus.bus_name}": {duplicate_name} -> {canonical_name}')

                # Update user preferences M2M as well
                for pref in UserBusPreference.objects.filter(preferred_amenities=duplicate_amenity):
                    pref.preferred_amenities.remove(duplicate_amenity)
                    pref.preferred_amenities.add(canonical_amenity)
                    self.stdout.write(f'Updated preference for user {pref.user_id}: {duplicate_name} -> {canonical_name}')
                
                # Delete the duplicate
                duplicate_amenity.delete()
                self.stdout.write(f'Merged "{duplicate_name}" into "{canonical_name}"')
                
            except BusAmenity.DoesNotExist:
                self.stdout.write(f'Amenity "{duplicate_name}" or "{canonical_name}" not found, skipping...')
        
        # Update icons for amenities that might be missing them and normalize to icon name only (e.g., 'wifi')
        icon_updates = {
            'WiFi': 'wifi',
            'Air Conditioning': 'snowflake',
            'Entertainment': 'tv',
            'Music System': 'music',
            'Water Bottle': 'tint',
            'Charging Port': 'plug',
            'Meal Service': 'utensils',
            'Blanket & Pillow': 'bed',
            'Reading Light': 'lightbulb',
            'GPS Tracking': 'map-marker-alt',
            'Emergency Kit': 'first-aid',
            'CCTV': 'video',
        }

        def normalize_icon(icon_val: str):
            if not icon_val:
                return None
            # If value already just icon (no spaces), return
            if ' ' not in icon_val and not icon_val.startswith('fa-'):
                return icon_val
            # Extract last class that starts with 'fa-'
            parts = icon_val.split()
            for cls in reversed(parts):
                if cls.startswith('fa-'):
                    return cls.replace('fa-', '')
            # Fallback to original
            return icon_val
        
        # First normalize any existing icons that include full class names
        for amenity in BusAmenity.objects.all():
            normalized = normalize_icon(amenity.icon)
            if normalized and normalized != amenity.icon:
                amenity.icon = normalized
                amenity.save(update_fields=['icon'])
                self.stdout.write(f'Normalized icon for "{amenity.name}": {normalized}')
        
        # Then ensure canonical amenities have the expected icon value
        for amenity_name, icon in icon_updates.items():
            try:
                amenity = BusAmenity.objects.get(name=amenity_name)
                if amenity.icon != icon:
                    amenity.icon = icon
                    amenity.save(update_fields=['icon'])
                    self.stdout.write(f'Updated icon for "{amenity_name}": {icon}')
            except BusAmenity.DoesNotExist:
                self.stdout.write(f'Amenity "{amenity_name}" not found for icon update')
        
        self.stdout.write(self.style.SUCCESS('Amenity cleanup completed successfully!'))
        
        # Show final amenities list
        self.stdout.write('\nFinal amenities list:')
        for amenity in BusAmenity.objects.all().order_by('name'):
            self.stdout.write(f'  - {amenity.name} (icon: {amenity.icon or "None"})')
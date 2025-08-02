from django.core.management.base import BaseCommand
from buses.models import BusAmenity

class Command(BaseCommand):
    help = 'Remove duplicate amenities from the database'

    def handle(self, *args, **options):
        # Define the amenities we want to keep (with proper icons)
        desired_amenities = [
            {'name': 'WiFi', 'icon': 'fas fa-wifi', 'description': 'High-speed internet connectivity'},
            {'name': 'Charging Port', 'icon': 'fas fa-plug', 'description': 'USB and power charging ports'},
            {'name': 'Air Conditioning', 'icon': 'fas fa-snowflake', 'description': 'Climate controlled environment'},
            {'name': 'Entertainment', 'icon': 'fas fa-tv', 'description': 'TV and entertainment system'},
            {'name': 'Meal Service', 'icon': 'fas fa-utensils', 'description': 'Complimentary meals and snacks'},
            {'name': 'Blanket & Pillow', 'icon': 'fas fa-bed', 'description': 'Comfortable bedding for rest'},
            {'name': 'Reading Light', 'icon': 'fas fa-lightbulb', 'description': 'Individual reading lights'},
            {'name': 'Water Bottle', 'icon': 'fas fa-tint', 'description': 'Complimentary water service'},
            {'name': 'GPS Tracking', 'icon': 'fas fa-map-marker-alt', 'description': 'Real-time location tracking'},
            {'name': 'Emergency Kit', 'icon': 'fas fa-first-aid', 'description': 'Safety and emergency equipment'},
            {'name': 'CCTV', 'icon': 'fas fa-video', 'description': 'Security camera monitoring'},
            {'name': 'Music System', 'icon': 'fas fa-music', 'description': 'Audio entertainment system'},
        ]

        # Remove all existing amenities
        deleted_count = BusAmenity.objects.all().count()
        BusAmenity.objects.all().delete()
        self.stdout.write(f'Deleted {deleted_count} existing amenities')

        # Create the desired amenities
        created_count = 0
        for amenity_data in desired_amenities:
            amenity, created = BusAmenity.objects.get_or_create(
                name=amenity_data['name'],
                defaults={
                    'icon': amenity_data['icon'],
                    'description': amenity_data['description']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created amenity: {amenity.name}')

        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleaned up amenities. Created {created_count} new amenities.')
        )
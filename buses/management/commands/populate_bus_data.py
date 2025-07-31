from django.core.management.base import BaseCommand
from buses.models import BusType, BusAmenity, BusDriver

class Command(BaseCommand):
    help = 'Populate database with sample bus types, amenities, and drivers'
    
    def handle(self, *args, **options):
        # Create Bus Types
        bus_types = [
            {'name': 'Normal', 'description': 'Standard non-AC bus with basic seating'},
            {'name': 'AC Deluxe', 'description': 'Air-conditioned bus with comfortable seating'},
            {'name': 'Sleeper', 'description': 'Bus with sleeping berths for overnight travel'},
            {'name': 'Volvo AC', 'description': 'Premium Volvo bus with luxury amenities'},
            {'name': 'Semi Sleeper', 'description': 'Bus with reclining seats for comfortable travel'},
        ]
        
        for bus_type_data in bus_types:
            bus_type, created = BusType.objects.get_or_create(
                name=bus_type_data['name'],
                defaults={'description': bus_type_data['description']}
            )
            if created:
                self.stdout.write(f'Created bus type: {bus_type.name}')
            else:
                self.stdout.write(f'Bus type already exists: {bus_type.name}')
        
        # Create Bus Amenities
        amenities = [
            {'name': 'WiFi', 'icon': 'fas fa-wifi', 'description': 'Free wireless internet access'},
            {'name': 'Charging Port', 'icon': 'fas fa-plug', 'description': 'USB and power charging ports'},
            {'name': 'Air Conditioning', 'icon': 'fas fa-snowflake', 'description': 'Climate controlled environment'},
            {'name': 'Entertainment', 'icon': 'fas fa-tv', 'description': 'TV and music entertainment system'},
            {'name': 'Meal Service', 'icon': 'fas fa-utensils', 'description': 'Complimentary meals and snacks'},
            {'name': 'Blanket & Pillow', 'icon': 'fas fa-bed', 'description': 'Comfortable bedding for rest'},
            {'name': 'Reading Light', 'icon': 'fas fa-lightbulb', 'description': 'Individual reading lights'},
            {'name': 'Water Bottle', 'icon': 'fas fa-tint', 'description': 'Complimentary water bottle'},
            {'name': 'GPS Tracking', 'icon': 'fas fa-map-marker-alt', 'description': 'Real-time bus location tracking'},
            {'name': 'Emergency Kit', 'icon': 'fas fa-first-aid', 'description': 'First aid and emergency supplies'},
        ]
        
        for amenity_data in amenities:
            amenity, created = BusAmenity.objects.get_or_create(
                name=amenity_data['name'],
                defaults={
                    'icon': amenity_data['icon'],
                    'description': amenity_data['description']
                }
            )
            if created:
                self.stdout.write(f'Created amenity: {amenity.name}')
            else:
                self.stdout.write(f'Amenity already exists: {amenity.name}')
        
        # Create Sample Bus Drivers
        drivers = [
            {'name': 'Rajesh Kumar', 'license_number': 'NP001234567', 'contact_number': '+977-9876543210', 'experience_years': 8},
        {'name': 'Suresh Sharma', 'license_number': 'NP001234568', 'contact_number': '+977-9876543211', 'experience_years': 12},
        {'name': 'Mahesh Singh', 'license_number': 'NP001234569', 'contact_number': '+977-9876543212', 'experience_years': 5},
        {'name': 'Ramesh Gupta', 'license_number': 'NP001234570', 'contact_number': '+977-9876543213', 'experience_years': 15},
        {'name': 'Dinesh Yadav', 'license_number': 'NP001234571', 'contact_number': '+977-9876543214', 'experience_years': 7},
        {'name': 'Vikash Jha', 'license_number': 'NP001234572', 'contact_number': '+977-9876543215', 'experience_years': 10},
        {'name': 'Anil Verma', 'license_number': 'NP001234573', 'contact_number': '+977-9876543216', 'experience_years': 6},
        {'name': 'Santosh Mishra', 'license_number': 'NP001234574', 'contact_number': '+977-9876543217', 'experience_years': 9},
        ]
        
        for driver_data in drivers:
            driver, created = BusDriver.objects.get_or_create(
                license_number=driver_data['license_number'],
                defaults={
                    'name': driver_data['name'],
                    'contact_number': driver_data['contact_number'],
                    'experience_years': driver_data['experience_years']
                }
            )
            if created:
                self.stdout.write(f'Created driver: {driver.name}')
            else:
                self.stdout.write(f'Driver already exists: {driver.name}')
        
        self.stdout.write(self.style.SUCCESS('Successfully populated bus data!'))
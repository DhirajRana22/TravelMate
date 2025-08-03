from django.core.management.base import BaseCommand
from buses.models import BusType, Bus, UserBusPreference

class Command(BaseCommand):
    help = 'Remove duplicate bus types from the database'

    def handle(self, *args, **options):
        # Find the duplicate Semi Sleeper entries
        semi_sleeper_1 = BusType.objects.filter(name='Semi Sleeper').first()
        semi_sleeper_2 = BusType.objects.filter(name='Semi-Sleeper').first()
        
        if semi_sleeper_1 and semi_sleeper_2:
            self.stdout.write(f'Found duplicate Semi Sleeper types:')
            self.stdout.write(f'  - ID {semi_sleeper_1.id}: "{semi_sleeper_1.name}"')
            self.stdout.write(f'  - ID {semi_sleeper_2.id}: "{semi_sleeper_2.name}"')
            
            # Keep the one without hyphen and merge the other
            keep_type = semi_sleeper_1  # 'Semi Sleeper'
            remove_type = semi_sleeper_2  # 'Semi-Sleeper'
            
            # Update any buses that use the duplicate type
            buses_updated = Bus.objects.filter(bus_type=remove_type).update(bus_type=keep_type)
            self.stdout.write(f'Updated {buses_updated} buses to use "{keep_type.name}"')
            
            # Update any user preferences that use the duplicate type
            # For the bus_type field
            prefs_updated_1 = UserBusPreference.objects.filter(bus_type=remove_type).update(bus_type=keep_type)
            self.stdout.write(f'Updated {prefs_updated_1} user preferences (bus_type field) to use "{keep_type.name}"')
            
            # For the preferred_bus_types many-to-many field
            prefs_with_duplicate = UserBusPreference.objects.filter(preferred_bus_types=remove_type)
            prefs_updated_2 = 0
            for pref in prefs_with_duplicate:
                pref.preferred_bus_types.remove(remove_type)
                pref.preferred_bus_types.add(keep_type)
                prefs_updated_2 += 1
            self.stdout.write(f'Updated {prefs_updated_2} user preferences (preferred_bus_types field) to use "{keep_type.name}"')
            
            # Delete the duplicate type
            remove_type.delete()
            self.stdout.write(f'Deleted duplicate bus type: "{remove_type.name}"')
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up duplicate Semi Sleeper bus types.')
            )
        else:
            self.stdout.write('No duplicate Semi Sleeper types found.')
from django.core.management.base import BaseCommand
from buses.models import BusDriver

class Command(BaseCommand):
    help = 'Clean up unassigned drivers that are not needed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Actually delete the unassigned drivers (without this flag, only shows what would be deleted)',
        )

    def handle(self, *args, **options):
        unassigned_drivers = BusDriver.objects.filter(bus=None)
        
        if not unassigned_drivers.exists():
            self.stdout.write(self.style.SUCCESS("No unassigned drivers found. Nothing to clean up."))
            return

        self.stdout.write(f"Found {unassigned_drivers.count()} unassigned drivers:")
        for driver in unassigned_drivers:
            self.stdout.write(f"- {driver.name} (License: {driver.license_number}, Experience: {driver.experience_years} years)")

        if options['confirm']:
            deleted_count = unassigned_drivers.count()
            unassigned_drivers.delete()
            self.stdout.write(
                self.style.SUCCESS(f"Successfully deleted {deleted_count} unassigned drivers.")
            )
        else:
            self.stdout.write(
                self.style.WARNING("\nDry run mode. Use --confirm to actually delete these drivers.")
            )
            self.stdout.write("Command: python manage.py cleanup_unassigned_drivers --confirm")
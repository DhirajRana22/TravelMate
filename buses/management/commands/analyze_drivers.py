from django.core.management.base import BaseCommand
from buses.models import Bus, BusDriver

class Command(BaseCommand):
    help = 'Analyze bus drivers and their assignments'

    def handle(self, *args, **options):
        self.stdout.write("=== BUS AND DRIVER ANALYSIS ===")
        self.stdout.write(f"Total buses: {Bus.objects.count()}")
        self.stdout.write(f"Total drivers: {BusDriver.objects.count()}")

        self.stdout.write("\n=== BUSES AND THEIR DRIVERS ===")
        buses = Bus.objects.all()
        for bus in buses:
            driver = bus.drivers.first()
            driver_name = driver.name if driver else "No driver assigned"
            self.stdout.write(f"Bus: {bus.bus_name} ({bus.bus_number}) -> Driver: {driver_name}")

        self.stdout.write("\n=== UNASSIGNED DRIVERS ===")
        unassigned_drivers = BusDriver.objects.filter(bus=None)
        self.stdout.write(f"Count: {unassigned_drivers.count()}")
        for driver in unassigned_drivers:
            self.stdout.write(f"- {driver.name} (License: {driver.license_number}, Experience: {driver.experience_years} years)")

        self.stdout.write("\n=== ASSIGNED DRIVERS ===")
        assigned_drivers = BusDriver.objects.exclude(bus=None)
        self.stdout.write(f"Count: {assigned_drivers.count()}")
        for driver in assigned_drivers:
            self.stdout.write(f"- {driver.name} (License: {driver.license_number}) -> Bus: {driver.bus.bus_name}")

        if unassigned_drivers.exists():
            self.stdout.write("\n=== RECOMMENDATION ===")
            self.stdout.write(self.style.WARNING(f"Found {unassigned_drivers.count()} unassigned drivers that may be unnecessary."))
            self.stdout.write("These drivers were likely created by the populate_bus_data command but never assigned to buses.")
            self.stdout.write("You can safely delete them if they are not needed.")
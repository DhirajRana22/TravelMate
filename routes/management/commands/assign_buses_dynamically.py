from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta, time
from routes.models import Route, BusSchedule, DynamicBusAssignment
from buses.models import Bus

class Command(BaseCommand):
    help = 'Dynamically assign buses to routes based on travel duration and availability'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=30,
            help='Number of days ahead to generate assignments (default: 30)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regenerate assignments even if they exist'
        )
    
    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        force = options['force']
        
        self.stdout.write(f"Generating dynamic bus assignments for {days_ahead} days ahead...")
        
        # Clear existing assignments if force is True
        if force:
            DynamicBusAssignment.objects.filter(
                departure_date__gte=timezone.now().date()
            ).delete()
            self.stdout.write("Cleared existing future assignments.")
        
        # Get all active routes and buses
        routes = Route.objects.filter(is_active=True)
        buses = Bus.objects.filter(is_active=True)
        
        assignments_created = 0
        
        for route in routes:
            # Get base schedules for this route
            base_schedules = BusSchedule.objects.filter(
                route=route,
                is_active=True
            ).order_by('departure_time')
            
            if not base_schedules.exists():
                continue
                
            # Generate assignments for each day
            for day_offset in range(days_ahead):
                target_date = timezone.now().date() + timedelta(days=day_offset)
                
                # Skip if assignments already exist for this date and route
                if not force and DynamicBusAssignment.objects.filter(
                    current_route=route,
                    departure_date=target_date
                ).exists():
                    continue
                
                # Assign buses to schedules for this date
                for schedule in base_schedules:
                    if schedule.is_available_on_date(target_date):
                        assigned_bus = self.find_available_bus(
                            route, target_date, schedule.departure_time, buses
                        )
                        
                        if assigned_bus:
                            assignment = self.create_assignment(
                                assigned_bus, route, target_date, schedule
                            )
                            if assignment:
                                assignments_created += 1
                                self.stdout.write(
                                    f"Assigned {assigned_bus.bus_name} to {route} on {target_date} at {schedule.departure_time}"
                                )
        
        # Generate return journey assignments
        self.generate_return_journeys(days_ahead, force)
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {assignments_created} bus assignments.")
        )
    
    def find_available_bus(self, route, date, departure_time, buses):
        """Find an available bus for the given route, date, and time"""
        for bus in buses:
            # Check if bus is already assigned at this time
            existing_assignment = DynamicBusAssignment.objects.filter(
                bus=bus,
                departure_date=date,
                departure_time=departure_time
            ).first()
            
            if existing_assignment:
                continue
            
            # Check if bus is available (not on another route at this time)
            conflicting_assignments = DynamicBusAssignment.objects.filter(
                bus=bus,
                departure_date=date,
                departure_time__lte=departure_time,
                arrival_time__gte=departure_time
            )
            
            # For overnight journeys, also check previous day
            if departure_time < time(12, 0):  # Morning departure might conflict with overnight journey
                prev_date = date - timedelta(days=1)
                overnight_conflicts = DynamicBusAssignment.objects.filter(
                    bus=bus,
                    departure_date=prev_date,
                    arrival_date=date,
                    arrival_time__gte=departure_time
                )
                if overnight_conflicts.exists():
                    continue
            
            if not conflicting_assignments.exists():
                return bus
        
        return None
    
    def create_assignment(self, bus, route, date, schedule):
        """Create a dynamic bus assignment"""
        # Calculate arrival date and time
        departure_datetime = datetime.combine(date, schedule.departure_time)
        arrival_datetime = departure_datetime + schedule.journey_duration
        
        # Calculate next available time (add buffer time for cleaning, maintenance)
        buffer_hours = self.get_buffer_hours(schedule.journey_duration)
        next_available_datetime = arrival_datetime + timedelta(hours=buffer_hours)
        
        assignment = DynamicBusAssignment.objects.create(
            bus=bus,
            current_route=route,
            departure_date=date,
            departure_time=schedule.departure_time,
            arrival_date=arrival_datetime.date(),
            arrival_time=arrival_datetime.time(),
            next_available_date=next_available_datetime.date(),
            next_available_time=next_available_datetime.time()
        )
        
        return assignment
    
    def get_buffer_hours(self, journey_duration):
        """Get buffer hours based on journey duration"""
        total_hours = journey_duration.total_seconds() / 3600
        
        if total_hours <= 6:  # Short routes (up to 6 hours)
            return 2  # 2 hours buffer
        elif total_hours <= 12:  # Medium routes (6-12 hours)
            return 4  # 4 hours buffer
        else:  # Long routes (12+ hours)
            return 8  # 8 hours buffer
    
    def generate_return_journeys(self, days_ahead, force):
        """Generate return journey assignments based on existing assignments"""
        self.stdout.write("Generating return journey assignments...")
        
        return_assignments = 0
        
        # Get all assignments that could have return journeys
        assignments = DynamicBusAssignment.objects.filter(
            departure_date__gte=timezone.now().date(),
            departure_date__lte=timezone.now().date() + timedelta(days=days_ahead)
        )
        
        for assignment in assignments:
            # Find return route
            return_route = Route.objects.filter(
                source=assignment.current_route.destination,
                destination=assignment.current_route.source,
                is_active=True
            ).first()
            
            if not return_route:
                continue
            
            # Check if return assignment already exists
            if DynamicBusAssignment.objects.filter(
                bus=assignment.bus,
                current_route=return_route,
                departure_date=assignment.next_available_date,
                departure_time=assignment.next_available_time
            ).exists():
                continue
            
            # Find suitable return schedule
            return_schedules = BusSchedule.objects.filter(
                route=return_route,
                departure_time__gte=assignment.next_available_time,
                is_active=True
            ).order_by('departure_time')
            
            if return_schedules.exists():
                return_schedule = return_schedules.first()
                
                # Create return assignment
                return_assignment = self.create_assignment(
                    assignment.bus,
                    return_route,
                    assignment.next_available_date,
                    return_schedule
                )
                
                if return_assignment:
                    return_assignments += 1
                    self.stdout.write(
                        f"Created return journey: {assignment.bus.bus_name} from {return_route} on {assignment.next_available_date}"
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f"Created {return_assignments} return journey assignments.")
        )
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from dateutil.relativedelta import relativedelta


class ManifestValidator:
    def __init__(self, flight):
        self.flight = flight
        self.errors = []
        self.warnings = []

    def validate(self):
        # 1. Pilot Check (Point 5)
        if not self.flight.pilot_in_command:
            self.errors.append("Pilot in Command is missing. This is required for DGM submission.")

        # 2. Passenger Checks (Point 7 & 8)
        # Configurable passport validity (default 6 months)
        min_validity_months = getattr(settings, 'MANIFEST_MIN_PASSPORT_VALIDITY_MONTHS', 6)
        required_validity_date = self.flight.departure_datetime.date() + relativedelta(months=min_validity_months)

        for pax in self.flight.passengers.all():
            name = pax.passenger_name

            # Weight check (Point 4)
            if pax.bag_weight_kg is None:
                self.errors.append(f"{name} is missing baggage weight.")

            # Passport validity check
            expiry_date = None
            if pax.expert:
                expiry_date = pax.expert.passport_expiry_date
            elif pax.dependant:
                expiry_date = pax.dependant.passport_expiry_date

            if not expiry_date:
                self.errors.append(f"{name} has no passport expiry date on file.")
            elif expiry_date < required_validity_date:
                self.warnings.append(
                    f"{name}'s passport expires on {expiry_date} (less than {min_validity_months} months from flight date)."
                )

            # Visa & Carte checks for Experts
            if pax.expert:
                # Check for active carte de travail (FIXED related name)
                active_carte = pax.expert.cartes_de_travail.filter(
                    is_active=True,
                    expiry_date__gte=self.flight.departure_datetime.date()
                ).first()
                if not active_carte:
                    self.errors.append(f"{name} does not have a valid Carte de Travail for the flight date.")

                # Check for active Visa
                active_visa = pax.expert.visa_records.filter(
                    status="ACTIVE",
                    expiry_date__gte=self.flight.departure_datetime.date()
                ).first()
                if not active_visa:
                    self.errors.append(f"{name} does not have an active Visa for the flight date.")

        return self.errors, self.warnings
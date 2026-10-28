"""
Charter & Travel Management — flights, rotations, dependants, authorizations.
"""

import uuid
import hashlib
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from apps.experts.models import ExpertProfile


# ═══════════════════════════════════════════════════════════════
# 1. CHARTER OPERATORS (Kibali fleet + MAF, Serve Air, etc.)
# ═══════════════════════════════════════════════════════════════

class CharterOperator(models.Model):
    """Air operator — internal fleet or external charter/commercial."""

    class OperatorType(models.TextChoices):
        INTERNAL = "INTERNAL", _("Internal fleet (company-owned)")
        EXTERNAL_CHARTER = "EXTERNAL_CHARTER", _("External charter operator")
        COMMERCIAL = "COMMERCIAL", _("Commercial airline")
        MILITARY = "MILITARY", _("Military / government")
        MEDEVAC = "MEDEVAC", _("Medical evacuation specialist")

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    operator_type = models.CharField(max_length=30, choices=OperatorType.choices, db_index=True)
    iata_code = models.CharField(max_length=10, blank=True)
    icao_code = models.CharField(max_length=10, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    emergency_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["operator_type", "name"]
        verbose_name = "Charter Operator"
        verbose_name_plural = "Charter Operators"

    def __str__(self):
        return f"{self.name} ({self.code})"


# ═══════════════════════════════════════════════════════════════
# 2. AIRCRAFT
# ═══════════════════════════════════════════════════════════════

class Aircraft(models.Model):
    """A specific aircraft (e.g., Kibali's ZS-BGO)."""

    class AircraftType(models.TextChoices):
        FIXED_WING = "FIXED_WING", _("Fixed wing")
        HELICOPTER = "HELICOPTER", _("Helicopter")

    operator = models.ForeignKey(
        CharterOperator, on_delete=models.PROTECT, related_name="aircraft",
    )
    registration = models.CharField(max_length=20, unique=True)
    model_name = models.CharField(max_length=80, help_text="e.g., Beechcraft 1900D")
    aircraft_type = models.CharField(
        max_length=20, choices=AircraftType.choices,
        default=AircraftType.FIXED_WING,
    )
    capacity_passengers = models.PositiveIntegerField(default=19)
    has_medevac_config = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["operator", "registration"]
        verbose_name = "Aircraft"
        verbose_name_plural = "Aircraft"

    def __str__(self):
        return f"{self.registration} — {self.model_name}"


# ═══════════════════════════════════════════════════════════════
# 3. CHARTER ROUTES
# ═══════════════════════════════════════════════════════════════

class CharterRoute(models.Model):
    """A scheduled route (e.g., FIH → KGA)."""

    origin_iata = models.CharField(max_length=10, help_text="IATA code, e.g., FIH")
    origin_name = models.CharField(max_length=120, help_text="e.g., Kinshasa N'djili")
    destination_iata = models.CharField(max_length=10, help_text="e.g., KGA")
    destination_name = models.CharField(max_length=120, help_text="e.g., Kibali")
    typical_duration_minutes = models.PositiveIntegerField(default=120)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "origin_iata", "destination_iata"]
        verbose_name = "Charter Route"
        verbose_name_plural = "Charter Routes"
        unique_together = [("origin_iata", "destination_iata")]

    def __str__(self):
        return f"{self.origin_iata} → {self.destination_iata}"


# ═══════════════════════════════════════════════════════════════
# 4. CHARTER FLIGHTS
# ═══════════════════════════════════════════════════════════════

class CharterFlight(models.Model):
    """A specific scheduled flight."""

    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        BOARDING = "BOARDING", _("Boarding")
        DEPARTED = "DEPARTED", _("Departed")
        ARRIVED = "ARRIVED", _("Arrived")
        DELAYED = "DELAYED", _("Delayed")
        CANCELLED = "CANCELLED", _("Cancelled")
        DIVERTED = "DIVERTED", _("Diverted")
        MEDEVAC = "MEDEVAC", _("Medevac")

    class ManifestStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        SUBMITTED = "SUBMITTED", _("Submitted to DGM")
        APPROVED = "APPROVED", _("Approved by DGM")
        REJECTED = "REJECTED", _("Rejected by DGM")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flight_number = models.CharField(max_length=40, unique=True)
    operator = models.ForeignKey(
        CharterOperator, on_delete=models.PROTECT, related_name="flights",
    )
    aircraft = models.ForeignKey(
        Aircraft, on_delete=models.PROTECT, related_name="flights",
        null=True, blank=True,
    )
    route = models.ForeignKey(
        CharterRoute, on_delete=models.PROTECT, related_name="flights",
    )
    departure_datetime = models.DateTimeField(db_index=True)
    arrival_datetime = models.DateTimeField()
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.SCHEDULED, db_index=True,
    )
    seats_available = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)

    # PREMIUM MANIFEST FIELDS
    pilot_in_command = models.CharField(max_length=100, blank=True, null=True, help_text="Name of the Pilot in Command")
    manifest_status = models.CharField(max_length=20, choices=ManifestStatus.choices, default=ManifestStatus.DRAFT)
    manifest_hash = models.CharField(max_length=64, blank=True, null=True,
                                     help_text="SHA-256 hash of the finalized manifest")
    version = models.PositiveIntegerField(default=1)
    locked_at = models.DateTimeField(null=True, blank=True, help_text="Set when submitted to DGM to prevent edits")

    # DGM / regulatory
    dgm_manifest_submitted = models.BooleanField(default=False, db_index=True)
    dgm_manifest_submitted_at = models.DateTimeField(null=True, blank=True)

    # Medevac readiness
    medevac_ready = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-departure_datetime"]
        verbose_name = "Charter Flight"
        verbose_name_plural = "Charter Flights"
        indexes = [
            models.Index(fields=["departure_datetime", "status"]),
            models.Index(fields=["route", "departure_datetime"]),
        ]

    def __str__(self):
        return f"{self.flight_number} · {self.route} · {self.departure_datetime:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        # Generate a SHA-256 hash when the manifest is submitted to DGM
        if self.manifest_status == self.ManifestStatus.SUBMITTED and not self.manifest_hash:
            raw_string = f"{self.id}-{self.flight_number}-{self.version}-{timezone.now().isoformat()}"
            self.manifest_hash = hashlib.sha256(raw_string.encode()).hexdigest()
        super().save(*args, **kwargs)

    @property
    def is_locked(self):
        """Prevents edits if the manifest has been submitted to DGM."""
        return self.manifest_status in [self.ManifestStatus.SUBMITTED, self.ManifestStatus.APPROVED]

    @property
    def is_past(self):
        return self.departure_datetime < timezone.now()

    @property
    def passenger_count(self):
        return self.passengers.count()

    @property
    def total_bag_weight(self):
        """Calculates total checked baggage weight for the flight."""
        total = sum((p.bag_weight_kg or 0) for p in self.passengers.all())
        return total

    @property
    def has_missing_weights(self):
        """Returns True if any passenger is missing weight data."""
        return self.passengers.filter(bag_weight_kg__isnull=True).exists() or self.passengers.filter(
            bag_count=0).exists()

    @property
    def display_total_weight(self):
        if self.has_missing_weights:
            return "Incomplet / Incomplete"
        return f"{self.total_bag_weight} kg"


# ═══════════════════════════════════════════════════════════════
# 5. DEPENDANTS (family members)
# ═══════════════════════════════════════════════════════════════

class Dependant(models.Model):
    """A family member of an expert (spouse, child, etc.)."""

    class RelationType(models.TextChoices):
        SPOUSE = "SPOUSE", _("Spouse")
        CHILD = "CHILD", _("Child")
        PARENT = "PARENT", _("Parent")
        SIBLING = "SIBLING", _("Sibling")
        OTHER = "OTHER", _("Other")

    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="dependants",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    relationship = models.CharField(max_length=20, choices=RelationType.choices)
    nationality = models.CharField(max_length=100)
    passport_number = EncryptedCharField(max_length=50, blank=True)
    passport_expiry_date = models.DateField(null=True, blank=True)
    yellow_fever_expiry_date = models.DateField(null=True, blank=True)
    is_travel_eligible = models.BooleanField(
        default=True,
        help_text="Whether this person may book flights.",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expert", "date_of_birth"]
        verbose_name = "Dependant"
        verbose_name_plural = "Dependants"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_relationship_display()} of {self.expert.full_name})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


# ═══════════════════════════════════════════════════════════════
# 6. CHARTER PASSENGERS
# ═══════════════════════════════════════════════════════════════

class CharterPassenger(models.Model):
    """A passenger assigned to a specific flight."""

    class PassengerType(models.TextChoices):
        EXPERT = "EXPERT", _("Expatriate Expert")
        DEPENDANT = "DEPENDANT", _("Family Dependant")
        CREW = "CREW", _("Flight Crew")
        VIP = "VIP", _("VIP / Executive")
        MEDICAL = "MEDICAL", _("Medical / Medevac")

    class BookingStatus(models.TextChoices):
        RESERVED = "RESERVED", _("Reserved")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        CHECKED_IN = "CHECKED_IN", _("Checked in")
        BOARDED = "BOARDED", _("Boarded")
        NO_SHOW = "NO_SHOW", _("No-show")
        CANCELLED = "CANCELLED", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flight = models.ForeignKey(
        CharterFlight, on_delete=models.CASCADE, related_name="passengers",
    )
    passenger_type = models.CharField(max_length=20, choices=PassengerType.choices)

    # Exactly one of these should be set
    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE,
        null=True, blank=True, related_name="flights",
    )
    dependant = models.ForeignKey(
        Dependant, on_delete=models.CASCADE,
        null=True, blank=True, related_name="flights",
    )

    seat_number = models.CharField(max_length=10, blank=True)
    status = models.CharField(
        max_length=20, choices=BookingStatus.choices,
        default=BookingStatus.RESERVED, db_index=True,
    )
    booking_reference = models.CharField(max_length=30, blank=True)

    # Cost tracking
    ticket_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
    )
    is_company_paid = models.BooleanField(default=True)

    special_requests = models.TextField(blank=True)

    # PREMIUM MANIFEST FIELDS
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True,
                                    help_text="Passenger weight in kg")
    bag_count = models.PositiveIntegerField(default=0, help_text="Number of checked bags")
    bag_weight_kg = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True,
                                        help_text="Total baggage weight in kg")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["flight", "seat_number"]
        verbose_name = "Charter Passenger"
        verbose_name_plural = "Charter Passengers"
        unique_together = [
            ("flight", "seat_number"),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.passenger_type in (self.PassengerType.CREW, self.PassengerType.VIP):
            return
        if bool(self.expert) == bool(self.dependant):
            raise ValidationError(
                "Passenger must be either an expert OR a dependant — not both, not neither."
            )

    def __str__(self):
        who = self.expert.full_name if self.expert else (
            self.dependant.full_name if self.dependant else "—"
        )
        return f"{who} → {self.flight.flight_number}"

    @property
    def passenger_name(self):
        if self.expert:
            return self.expert.full_name
        if self.dependant:
            return self.dependant.full_name
        return "—"

    @property
    def passport_number(self):
        if self.expert:
            return self.expert.passport_number
        if self.dependant:
            return self.dependant.passport_number
        return ""

    @property
    def nationality(self):
        if self.expert:
            return self.expert.nationality
        if self.dependant:
            return self.dependant.nationality
        return ""

    @property
    def company_name(self):
        if self.expert:
            return self.expert.company.name
        if self.dependant and self.dependant.expert:
            return self.dependant.expert.company.name
        return "—"

    @property
    def department_name(self):
        if self.expert:
            return self.expert.department.name if self.expert.department else "—"
        if self.dependant and self.dependant.expert and self.dependant.expert.department:
            return self.dependant.expert.department.name
        return "—"


# ═══════════════════════════════════════════════════════════════
# 7. ROTATION SCHEDULES
# ═══════════════════════════════════════════════════════════════

class RotationSchedule(models.Model):
    """Expert's on-site / off-site rotation cycle."""

    class RotationPattern(models.TextChoices):
        R4_4 = "4_4", _("4 weeks on / 4 weeks off")
        R6_3 = "6_3", _("6 weeks on / 3 weeks off")
        R8_4 = "8_4", _("8 weeks on / 4 weeks off")
        R9_3 = "9_3", _("9 weeks on / 3 weeks off")
        R28_28 = "28_28", _("28 days on / 28 days off")
        CUSTOM = "CUSTOM", _("Custom")

    expert = models.OneToOneField(
        ExpertProfile, on_delete=models.CASCADE, related_name="rotation",
    )
    pattern = models.CharField(
        max_length=20, choices=RotationPattern.choices,
        default=RotationPattern.R4_4,
    )
    cycle_start_date = models.DateField(
        help_text="Date the current cycle began (start of ON period).",
    )
    custom_days_on = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Only used when pattern = CUSTOM.",
    )
    custom_days_off = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Only used when pattern = CUSTOM.",
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rotation Schedule"
        verbose_name_plural = "Rotation Schedules"

    def __str__(self):
        return f"{self.expert.full_name} — {self.get_pattern_display()}"

    @property
    def days_on(self):
        if self.pattern == self.RotationPattern.CUSTOM:
            return self.custom_days_on or 0
        mapping = {
            self.RotationPattern.R4_4: 28,
            self.RotationPattern.R6_3: 42,
            self.RotationPattern.R8_4: 56,
            self.RotationPattern.R9_3: 63,
            self.RotationPattern.R28_28: 28,
        }
        return mapping.get(self.pattern, 28)

    @property
    def days_off(self):
        if self.pattern == self.RotationPattern.CUSTOM:
            return self.custom_days_off or 0
        mapping = {
            self.RotationPattern.R4_4: 28,
            self.RotationPattern.R6_3: 21,
            self.RotationPattern.R8_4: 28,
            self.RotationPattern.R9_3: 21,
            self.RotationPattern.R28_28: 28,
        }
        return mapping.get(self.pattern, 28)

    @property
    def is_on_site(self):
        """Compute if today is within the ON phase."""
        from datetime import date
        if not self.cycle_start_date:
            return None
        total = self.days_on + self.days_off
        if total == 0:
            return None
        days_since_start = (date.today() - self.cycle_start_date).days
        if days_since_start < 0:
            return False
        phase_day = days_since_start % total
        return phase_day < self.days_on


# ═══════════════════════════════════════════════════════════════
# 8. TRAVEL AUTHORIZATIONS
# ═══════════════════════════════════════════════════════════════

class TravelAuthorization(models.Model):
    """Approval workflow for a travel request — dual approval (Manager → HR)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        PENDING_MANAGER = "PENDING_MANAGER", _("Pending Manager Approval")
        PENDING_HR = "PENDING_HR", _("Pending HR Approval")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        CANCELLED = "CANCELLED", _("Cancelled")
        COMPLETED = "COMPLETED", _("Completed")

    class Purpose(models.TextChoices):
        ROTATION = "ROTATION", _("Rotation (on/off)")
        BUSINESS = "BUSINESS", _("Business travel")
        MEDEVAC = "MEDEVAC", _("Medical evacuation")
        FAMILY_VISIT = "FAMILY_VISIT", _("Family visit")
        REPATRIATION = "REPATRIATION", _("Repatriation")
        TRAINING = "TRAINING", _("Training")
        OTHER = "OTHER", _("Other")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_number = models.CharField(max_length=40, unique=True)

    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.PROTECT, related_name="travel_authorizations",
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices, db_index=True)
    route = models.ForeignKey(
        CharterRoute, on_delete=models.PROTECT, related_name="authorizations",
        null=True, blank=True,
    )
    requested_departure_date = models.DateField()
    requested_return_date = models.DateField(null=True, blank=True)
    accompanying_dependants = models.ManyToManyField(
        Dependant, blank=True, related_name="travel_authorizations",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True,
    )

    # Manager approval
    manager_approved_by_id = models.IntegerField(null=True, blank=True)
    manager_approved_by_repr = models.CharField(max_length=255, blank=True)
    manager_approved_at = models.DateTimeField(null=True, blank=True)

    # HR approval
    hr_approved_by_id = models.IntegerField(null=True, blank=True)
    hr_approved_by_repr = models.CharField(max_length=255, blank=True)
    hr_approved_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)
    justification = models.TextField(blank=True)

    # Link to final flight (if booked)
    flight = models.ForeignKey(
        CharterFlight, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="authorizations",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Travel Authorization"
        verbose_name_plural = "Travel Authorizations"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["expert", "status"]),
        ]

    def __str__(self):
        return f"{self.request_number} — {self.expert.full_name} ({self.get_status_display()})"

    @property
    def is_fully_approved(self):
        return self.status == self.Status.APPROVED
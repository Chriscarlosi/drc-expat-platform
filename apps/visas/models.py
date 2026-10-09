"""
DRC Visa Engine — all visa types, catalog, prolongations, unified records.
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from apps.experts.models import ExpertProfile


# ═══════════════════════════════════════════════════════════════
# CARTE DE TRAVAIL
# ═══════════════════════════════════════════════════════════════

class CarteDeTravail(models.Model):
    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.PROTECT,
        related_name="cartes_de_travail",
    )
    permit_number = EncryptedCharField(max_length=50, unique=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    issuing_authority = models.CharField(max_length=200, default="Ministère du Travail")
    scan = models.FileField(upload_to="work_permits/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issue_date"]
        verbose_name = "Carte de Travail"
        verbose_name_plural = "Cartes de Travail"

    def __str__(self):
        return f"Carte {self.permit_number} — {self.expert.full_name}"

    def clean(self):
        if self.issue_date and self.expiry_date and self.expiry_date <= self.issue_date:
            raise ValidationError("Expiry date must be after issue date.")

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days


# ═══════════════════════════════════════════════════════════════
# LEGACY VISA (abstract base + 4 subclasses — kept for compatibility)
# ═══════════════════════════════════════════════════════════════

class Visa(models.Model):
    class VisaType(models.TextChoices):
        FLYING = "FLYING", "Flying Visa (Visa Volant)"
        AIRPORT = "AIRPORT", "Airport/Port Visa (Visa Aéroportuaire)"
        VOYAGE = "VOYAGE", "Travel Visa (Visa de Voyage)"
        ESTABLISHMENT = "ESTABLISHMENT", "Establishment Visa (Visa d'Établissement)"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        EXPIRING_SOON = "EXPIRING_SOON", "Expiring Soon"
        EXPIRED = "EXPIRED", "Expired"
        IRREGULAR = "IRREGULAR", "Irregular"
        CANCELLED = "CANCELLED", "Cancelled"

    class Meta:
        abstract = True

    visa_type = None
    visa_number = EncryptedCharField(max_length=50, unique=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    dgm_reference = models.CharField(max_length=100, blank=True)
    dgm_authorization_scan = models.FileField(upload_to="dgm_authorizations/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.visa_type} — {self.visa_number}"

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days


class FlyingVisa(Visa):
    expert = models.ForeignKey(ExpertProfile, on_delete=models.PROTECT, related_name="flying_visas")
    authorization_issued_date = models.DateField()
    utilization_deadline = models.DateField(help_text="Must be used within 3 months.")
    arrived = models.BooleanField(default=False)
    arrival_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Flying Visa (Visa Volant)"

    def clean(self):
        if self.authorization_issued_date and self.utilization_deadline:
            if (self.utilization_deadline - self.authorization_issued_date).days > 92:
                raise ValidationError("Visa Volant: window cannot exceed 3 months (92 days).")

    def save(self, *args, **kwargs):
        self.visa_type = self.VisaType.FLYING
        super().save(*args, **kwargs)


class AirportVisa(Visa):
    expert = models.ForeignKey(ExpertProfile, on_delete=models.PROTECT, related_name="airport_visas")
    arrival_date = models.DateField()
    arrival_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Airport Visa (Visa Aéroportuaire)"

    def save(self, *args, **kwargs):
        self.visa_type = self.VisaType.AIRPORT
        super().save(*args, **kwargs)

    @property
    def hours_since_arrival(self):
        if not self.arrival_time:
            return None
        return (timezone.now() - self.arrival_time).total_seconds() / 3600

    @property
    def is_in_critical_window(self):
        h = self.hours_since_arrival
        return h is not None and 0 <= h <= 48


class VoyageVisa(Visa):
    class EntryType(models.TextChoices):
        SINGLE = "SINGLE", "Single Entry"
        MULTIPLE = "MULTIPLE", "Multiple Entries"

    expert = models.ForeignKey(ExpertProfile, on_delete=models.PROTECT, related_name="voyage_visas")
    entry_type = models.CharField(max_length=10, choices=EntryType.choices, default=EntryType.SINGLE)

    class Meta:
        verbose_name = "Travel Visa (Visa de Voyage)"

    def clean(self):
        if self.issue_date and self.expiry_date:
            days = (self.expiry_date - self.issue_date).days
            if days < 28:
                raise ValidationError("Visa de Voyage: minimum validity is 1 month.")
            if days > 186:
                raise ValidationError("Visa de Voyage: maximum validity is 6 months.")

    def save(self, *args, **kwargs):
        self.visa_type = self.VisaType.VOYAGE
        super().save(*args, **kwargs)


class EstablishmentVisa(Visa):
    class EstablishmentType(models.TextChoices):
        WORK = "TRAVAIL", "Work Visa (Visa de Travail)"
        ORDINARY = "ORDINAIRE", "Ordinary Visa (Visa Ordinaire)"

    expert = models.ForeignKey(ExpertProfile, on_delete=models.PROTECT, related_name="establishment_visas")
    establishment_type = models.CharField(max_length=10, choices=EstablishmentType.choices)
    carte_de_travail = models.ForeignKey(
        CarteDeTravail, on_delete=models.PROTECT, null=True, blank=True,
        related_name="establishment_visas",
    )

    class Meta:
        verbose_name = "Establishment Visa (Visa d'Établissement)"

    def clean(self):
        if (self.establishment_type == self.EstablishmentType.WORK
                and self.status == self.Status.ACTIVE):
            if not self.carte_de_travail:
                raise ValidationError(
                    "A Work Visa cannot be Active without a valid Carte de Travail."
                )
            if self.carte_de_travail.expiry_date < self.expiry_date:
                raise ValidationError(
                    f"Carte de Travail expires ({self.carte_de_travail.expiry_date}) "
                    f"before visa expiry ({self.expiry_date})."
                )

    def save(self, *args, **kwargs):
        self.visa_type = self.VisaType.ESTABLISHMENT
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════
# VISA TYPE CATALOG
# ═══════════════════════════════════════════════════════════════

class VisaTypeCatalog(models.Model):
    class Category(models.TextChoices):
        FLYING = "FLYING", "Flying (Volant)"
        AIRPORT = "AIRPORT", "Airport/Port (Aéroportuaire)"
        VOYAGE = "VOYAGE", "Voyage"
        ESTABLISHMENT = "ESTABLISHMENT", "Établissement"
        PROLONGATION = "PROLONGATION", "Prolongation"
        TRANSIT = "TRANSIT", "Transit"
        ELECTRONIC = "ELECTRONIC", "Electronic / E-Visa"
        HOLIDAY = "HOLIDAY", "Holiday / Congé"

    code = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices)
    name_en = models.CharField(max_length=150)
    name_fr = models.CharField(max_length=150)
    description_en = models.TextField(blank=True)
    description_fr = models.TextField(blank=True)
    min_validity_days = models.PositiveIntegerField(default=1)
    max_validity_days = models.PositiveIntegerField(default=365)
    allows_multiple_entries = models.BooleanField(default=False)
    requires_carte_de_travail = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        verbose_name = "Visa Type Catalog"
        verbose_name_plural = "Visa Type Catalog"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} — {self.name_en}"


# ═══════════════════════════════════════════════════════════════
# UNIFIED VISA RECORD
# ═══════════════════════════════════════════════════════════════

class VisaRecord(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        EXPIRING_SOON = "EXPIRING_SOON", "Expiring Soon"
        EXPIRED = "EXPIRED", "Expired"
        IRREGULAR = "IRREGULAR", "Irregular"
        CANCELLED = "CANCELLED", "Cancelled"
        TRANSFERRED = "TRANSFERRED", "Transferred"

    expert = models.ForeignKey(ExpertProfile, on_delete=models.PROTECT, related_name="visa_records")
    visa_type = models.ForeignKey(VisaTypeCatalog, on_delete=models.PROTECT, related_name="visa_records")
    visa_number = EncryptedCharField(max_length=50, unique=True)
    issue_date = models.DateField()
    expiry_date = models.DateField(db_index=True)
    entry_date = models.DateField(null=True, blank=True)
    dgm_reference = models.CharField(max_length=100, blank=True)
    dgm_authorization_scan = models.FileField(upload_to="dgm_authorizations/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Visa Record"
        verbose_name_plural = "Visa Records"
        ordering = ["-issue_date"]
        indexes = [
            models.Index(fields=["expert", "status"]),
            models.Index(fields=["expiry_date", "status"]),
        ]

    def __str__(self):
        return f"{self.visa_type.code} — {self.expert.full_name}"

    @property
    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days

    @property
    def is_expired(self):
        return self.days_until_expiry < 0


# ═══════════════════════════════════════════════════════════════
# VISA PROLONGATION
# ═══════════════════════════════════════════════════════════════

class VisaProlongation(models.Model):
    class ProlongationType(models.TextChoices):
        VV2_PLUS = "VV2+", "VV2+ (2-month extension)"
        PVV3_PLUS = "PVV3+", "PVV3+ (3-month priority extension)"
        VV6 = "VV6", "VV6 (6-month extension)"
        VSR_PLUS = "VSR+", "VSR+ (Regular stay extension)"
        OTHER = "OTHER", "Other"

    expert = models.ForeignKey(ExpertProfile, on_delete=models.PROTECT, related_name="visa_prolongations")
    parent_visa = models.ForeignKey(VisaRecord, on_delete=models.PROTECT, related_name="prolongations")
    prolongation_type = models.CharField(max_length=20, choices=ProlongationType.choices)
    prolongation_number = EncryptedCharField(max_length=50)
    request_date = models.DateField()
    approval_date = models.DateField(null=True, blank=True)
    new_expiry_date = models.DateField()
    dgm_reference = models.CharField(max_length=100, blank=True)
    scan = models.FileField(upload_to="prolongations/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Visa Prolongation"
        verbose_name_plural = "Visa Prolongations"
        ordering = ["-request_date"]

    def __str__(self):
        return f"{self.prolongation_type} for {self.expert.full_name}"
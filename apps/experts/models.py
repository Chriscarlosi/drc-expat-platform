"""
Expert Profile — identity + employment data for foreign experts in DRC.

Tenant-scoped: every profile belongs to exactly one Company.
"""

from __future__ import annotations

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from apps.organization.models import Company, Site, Department
from apps.organization.managers import TenantManager


class ExpertProfile(models.Model):
    """Identity record for a foreign expert operating in the DRC."""

    class Gender(models.TextChoices):
        MALE = "M", _("Male / Masculin")
        FEMALE = "F", _("Female / Féminin")
        OTHER = "O", _("Other / Autre")

    class JobCategory(models.TextChoices):
        """
        Job-level categories per Ministerial Decree 2005.
        Each category has a maximum expat percentage under DRC law.
        """
        CLASS_I_V = "CLASS_I_V", _("Class I-V (Workers) — 2% cap")
        SUPERVISOR = "SUPERVISOR", _("Supervisor / Manager — 2.5% cap")
        MANAGEMENT = "MANAGEMENT", _("Management — 2% cap")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ─── Managers (tenant-scoped) ─────────────────────────────
    objects = TenantManager()

    # ─── Tenant scoping ──────────────────────────────────────────
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="experts",
        null=True, blank=True,
        help_text=_("The employer company (tenant) that owns this expert."),
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="experts",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="experts",
    )

    # Link to auth user (for read-only dashboard access later)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expert_profile",
        null=True, blank=True,
    )

    # ─── Identity ────────────────────────────────────────────────
    first_name = models.CharField(_("First name"), max_length=100, db_index=True)
    last_name = models.CharField(_("Last name"), max_length=100, db_index=True)
    date_of_birth = models.DateField(_("Date of birth"))
    gender = models.CharField(max_length=1, choices=Gender.choices)
    nationality = models.CharField(_("Nationality"), max_length=100, db_index=True)
    is_expatriate = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("False if this person is a DRC national."),
    )

    # ─── Passport (AES-256 encrypted) ────────────────────────────
    passport_number = EncryptedCharField(max_length=50, unique=True)
    passport_issue_date = models.DateField()
    passport_expiry_date = models.DateField(db_index=True)
    passport_scan = models.FileField(upload_to="passports/", null=True, blank=True)

    # ─── Health ──────────────────────────────────────────────────
    yellow_fever_card_number = EncryptedCharField(max_length=50, blank=True)
    yellow_fever_expiry_date = models.DateField(null=True, blank=True, db_index=True)
    yellow_fever_scan = models.FileField(upload_to="health/", null=True, blank=True)

    # ─── Labour Registry ─────────────────────────────────────────
    onem_registry_number = models.CharField(max_length=50, blank=True)

    # ─── Employment ──────────────────────────────────────────────
    employer_company = models.CharField(max_length=200)
    job_title = models.CharField(max_length=150)
    job_title_fr = models.CharField(max_length=150, blank=True)
    job_category = models.CharField(
        _("Job category (DRC)"),
        max_length=20,
        choices=JobCategory.choices,
        default=JobCategory.CLASS_I_V,
        db_index=True,
        help_text=_("Determines the expat cap for this role."),
    )

    # ─── Contact ─────────────────────────────────────────────────
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)

    # ─── Lifecycle ───────────────────────────────────────────────
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = _("Expert Profile")
        verbose_name_plural = _("Expert Profiles")
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "is_expatriate", "is_active"]),
            models.Index(fields=["passport_expiry_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.last_name}, {self.first_name} ({self.nationality})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
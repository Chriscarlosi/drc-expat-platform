"""
Organization domain — Company, Site, Department.

This is the multi-tenancy foundation. Every tenant-scoped record
(Experts, Visas, Penalties) links back to a Company.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Abstract base: adds created/updated timestamps + soft-delete."""

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    is_deleted = models.BooleanField(_("Soft deleted"), default=False, db_index=True)

    class Meta:
        abstract = True


class Company(TimeStampedModel):
    """
    A tenant. In our SaaS context: one mining company.

    Example: Kibali Gold Mine (Barrick DRC).
    """

    name = models.CharField(_("Legal name"), max_length=255, unique=True)
    slug = models.SlugField(_("URL slug"), max_length=100, unique=True)
    dgm_registration = models.CharField(
        _("DGM registration number"),
        max_length=100, blank=True,
        help_text="Direction Générale de Migration identifier",
    )
    tax_id = models.CharField(_("DRC tax ID (DGI)"), max_length=100, blank=True)
    onem_registry = models.CharField(_("ONEM employer registry"), max_length=100, blank=True)

    # Workforce baseline for quota calculation
    congolese_staff_count = models.PositiveIntegerField(
        _("Total Congolese staff"),
        default=0,
        help_text="Used to compute the 6.5% expatriate quota cap.",
    )

    contact_email = models.EmailField(_("Compliance contact email"), blank=True)
    contact_phone = models.CharField(_("Compliance contact phone"), max_length=30, blank=True)

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def total_staff(self) -> int:
        return self.congolese_staff_count + self.experts.filter(
            is_active=True, is_deleted=False
        ).count()


class Site(TimeStampedModel):
    """A physical operating site (e.g., Kibali's underground mine, processing plant)."""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="sites",
    )
    name = models.CharField(_("Site name"), max_length=150)
    code = models.CharField(_("Site code"), max_length=20)
    province = models.CharField(_("DRC province"), max_length=100, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Site")
        verbose_name_plural = _("Sites")
        unique_together = [("company", "code")]
        ordering = ["company", "name"]

    def __str__(self) -> str:
        return f"{self.company.name} — {self.name}"


class Department(TimeStampedModel):
    """Company department (HR, Operations, Mining, Processing...)."""

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="departments",
    )
    name = models.CharField(_("Department name"), max_length=150)
    code = models.CharField(_("Department code"), max_length=20)

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        unique_together = [("company", "code")]

    def __str__(self) -> str:
        return f"{self.company.name} — {self.name}"

    class UserCompanyMembership(TimeStampedModel):
        """
        Links a Django user to a Company with a role.

        A user can belong to multiple companies (e.g., a group with
        several DRC subsidiaries). Role controls what they can do.
        """

        class Role(models.TextChoices):
            OWNER = "OWNER", _("Owner")
            ADMIN = "ADMIN", _("Company Admin")
            HR_MANAGER = "HR_MANAGER", _("HR / Compliance Manager")
            VIEWER = "VIEWER", _("Read-only Viewer")

        user = models.ForeignKey(
            "auth.User",
            on_delete=models.CASCADE,
            related_name="company_memberships",
        )
        company = models.ForeignKey(
            Company,
            on_delete=models.CASCADE,
            related_name="user_memberships",
        )
        role = models.CharField(
            _("Role"),
            max_length=20,
            choices=Role.choices,
            default=Role.HR_MANAGER,
        )
        is_default = models.BooleanField(
            _("Default company for this user"),
            default=False,
            help_text=_("Used when the user first logs in."),
        )
        is_active = models.BooleanField(default=True, db_index=True)

        class Meta:
            verbose_name = _("User Company Membership")
            verbose_name_plural = _("User Company Memberships")
            unique_together = [("user", "company")]
            indexes = [
                models.Index(fields=["user", "is_active"]),
            ]

        def __str__(self) -> str:
            return f"{self.user.username} @ {self.company.name} ({self.get_role_display()})"


class UserCompanyMembership:
    pass
"""
Organization domain — Company, Site, Department, WorkforceSnapshot.

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

    # Workforce baseline for quota calculation (Legacy - now handled by WorkforceSnapshot)
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
    Links a Django user to a Company with a role and optional scope.

    A user can belong to multiple companies (e.g., a group with
    several DRC subsidiaries). Role controls WHAT they can do.
    Optional department/site scopes control WHICH records they see.
    """

    class Role(models.TextChoices):
        OWNER = "OWNER", _("Owner")
        ADMIN = "ADMIN", _("Company Admin")
        EXECUTIVE = "EXECUTIVE", _("Executive / GM (read-only)")
        HR_MANAGER = "HR_MANAGER", _("HR / Compliance Manager")
        DEPARTMENT_MANAGER = "DEPARTMENT_MANAGER", _("Department Manager")
        SITE_MANAGER = "SITE_MANAGER", _("Site Manager")
        EXPERT = "EXPERT", _("Expatriate Expert (self-service)")
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
        max_length=30,
        choices=Role.choices,
        default=Role.HR_MANAGER,
    )

    # ─── Optional scopes (for Department/Site Managers) ─────
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="user_memberships",
        help_text=_("If set, this user sees only experts in this department."),
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="user_memberships",
        help_text=_("If set, this user sees only experts at this site."),
    )

    # ─── Optional link to their own expert profile (for EXPERT role) ─
    expert_profile = models.ForeignKey(
        "experts.ExpertProfile",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="user_memberships",
        help_text=_("If this user is themselves an expert, link to their profile."),
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
            models.Index(fields=["company", "role", "is_active"]),
        ]

    def __str__(self) -> str:
        scope = ""
        if self.department:
            scope = f" — Dept: {self.department.name}"
        elif self.site:
            scope = f" — Site: {self.site.name}"
        return f"{self.user.username} @ {self.company.name} ({self.get_role_display()}){scope}"


class WorkforceSnapshot(models.Model):
    """
    Historical snapshot of a company's workforce for quota calculations.
    Per DRC Ministerial Decree 2005, quotas are per-category.
    Every edit is audited. If the latest snapshot is >31 days old, the
    quota hard cap is NOT applied, and a warning is shown instead.
    """
    company = models.ForeignKey(
        'Company', on_delete=models.CASCADE, related_name='workforce_snapshots'
    )
    snapshot_date = models.DateField()

    # Aggregate totals
    total_congolese_staff = models.PositiveIntegerField(default=0)
    total_expat_staff = models.PositiveIntegerField(default=0)

    # Per-category breakdown (Congolese)
    congolese_class_i_v = models.PositiveIntegerField(default=0)
    congolese_supervisor = models.PositiveIntegerField(default=0)
    congolese_management = models.PositiveIntegerField(default=0)

    # Per-category breakdown (Expat)
    expat_class_i_v = models.PositiveIntegerField(default=0)
    expat_supervisor = models.PositiveIntegerField(default=0)
    expat_management = models.PositiveIntegerField(default=0)

    # Supporting document and notes
    supporting_document = models.FileField(
        upload_to="workforce_docs/",
        null=True,
        blank=True,
        help_text="Upload a payroll summary or HR report."
    )
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='workforce_snapshots_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-snapshot_date', '-created_at']
        verbose_name = 'Workforce Snapshot'
        verbose_name_plural = 'Workforce Snapshots'
        indexes = [models.Index(fields=['company', '-snapshot_date'])]

    def __str__(self):
        return f"{self.company.name} — {self.snapshot_date} ({self.total_expat_staff}E / {self.total_congolese_staff}C)"

    @property
    def total_workforce(self):
        return self.total_congolese_staff + self.total_expat_staff

    @property
    def expat_pct(self):
        if self.total_workforce == 0:
            return 0.0
        return round(self.total_expat_staff / self.total_workforce * 100, 2)

    @property
    def is_stale(self):
        from django.utils import timezone
        return (timezone.now().date() - self.snapshot_date).days > 31

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.total_congolese_staff > 0:
            cat_sum = self.congolese_class_i_v + self.congolese_supervisor + self.congolese_management
            if cat_sum != self.total_congolese_staff:
                raise ValidationError(
                    f"Congolese category breakdown ({cat_sum}) does not match the "
                    f"total Congolese staff ({self.total_congolese_staff})."
                )
        if self.total_expat_staff > 0:
            cat_sum = self.expat_class_i_v + self.expat_supervisor + self.expat_management
            if cat_sum != self.total_expat_staff:
                raise ValidationError(
                    f"Expat category breakdown ({cat_sum}) does not match the "
                    f"total expat staff ({self.total_expat_staff})."
                )
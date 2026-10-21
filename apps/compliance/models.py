"""
Risk & Penalty Mitigation — DGM fines, cost tracking, monthly invoicing, export audit.
"""

import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.experts.models import ExpertProfile


# ═══════════════════════════════════════════════════════════════
# 1. PENALTY LEDGER — DGM overstay fines
# ═══════════════════════════════════════════════════════════════

class PenaltyLedger(models.Model):
    """Tracks accruing DGM daily overstay fines ($100–$300/day)."""

    class Reason(models.TextChoices):
        OVERSTAY = "OVERSTAY", "Overstay / Dépassement"
        NO_PERMIT = "NO_PERMIT", "Working without permit / Travail sans permis"
        EXPIRED_VISA = "EXPIRED_VISA", "Expired visa / Visa expiré"
        OTHER = "OTHER", "Other / Autre"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.PROTECT, related_name="penalties",
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    accrual_start_date = models.DateField()
    accrual_end_date = models.DateField(null=True, blank=True)
    daily_rate_usd = models.DecimalField(
        max_digits=8, decimal_places=2, default=100.00,
        help_text="DGM daily rate, typically $100–$300 USD.",
    )
    resolved = models.BooleanField(default=False)
    resolution_date = models.DateField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-accrual_start_date"]
        verbose_name = "Penalty Ledger Entry"
        verbose_name_plural = "Penalty Ledger"

    def __str__(self):
        return f"Penalty — {self.expert.full_name} — {self.total_amount_usd} USD"

    @property
    def days_accrued(self):
        end = self.accrual_end_date or timezone.now().date()
        return max(0, (end - self.accrual_start_date).days)

    @property
    def total_amount_usd(self):
        return self.days_accrued * self.daily_rate_usd

    @property
    def days_overdue(self):
        """Days since accrual started."""
        end = self.accrual_end_date or timezone.now().date()
        return max(0, (end - self.accrual_start_date).days)

    @property
    def is_critical(self):
        return self.days_overdue >= 30


# ═══════════════════════════════════════════════════════════════
# 2. COST CATEGORIES — configurable
# ═══════════════════════════════════════════════════════════════

class CostCategory(models.Model):
    """Configurable cost categories — HR/finance can extend from admin."""

    code = models.CharField(max_length=30, unique=True)
    name_en = models.CharField(max_length=150)
    name_fr = models.CharField(max_length=150)
    is_billable = models.BooleanField(
        default=True,
        help_text="Whether this cost can be recharged to the client company.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=100)

    class Meta:
        verbose_name = "Cost Category"
        verbose_name_plural = "Cost Categories"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} — {self.name_en}"


# ═══════════════════════════════════════════════════════════════
# 3. EXPERT COSTS
# ═══════════════════════════════════════════════════════════════

class ExpertCost(models.Model):
    """Individual cost line attached to an expert."""

    class Currency(models.TextChoices):
        USD = "USD", "USD ($)"
        CDF = "CDF", "CDF (Franc Congolais)"
        EUR = "EUR", "EUR (€)"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        INVOICED = "INVOICED", "Invoiced"
        PAID = "PAID", "Paid"
        DISPUTED = "DISPUTED", "Disputed"

    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.PROTECT, related_name="costs",
    )
    category = models.ForeignKey(
        CostCategory, on_delete=models.PROTECT, related_name="expert_costs",
    )
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.USD,
    )
    amount_usd = models.DecimalField(
        max_digits=12, decimal_places=2,
        editable=False, default=0,
        help_text="Converted amount in USD.",
    )
    incurred_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True,
    )
    invoice_number = models.CharField(max_length=50, blank=True, db_index=True)
    invoice_date = models.DateField(null=True, blank=True)
    receipt = models.FileField(upload_to="cost_receipts/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    _FX = {"USD": Decimal("1"), "EUR": Decimal("1.08"), "CDF": Decimal("0.00035714")}

    class Meta:
        ordering = ["-incurred_date"]
        verbose_name = "Expert Cost"
        verbose_name_plural = "Expert Costs"
        indexes = [
            models.Index(fields=["expert", "status"]),
            models.Index(fields=["incurred_date", "status"]),
            models.Index(fields=["invoice_number"]),
        ]

    def __str__(self):
        return f"{self.expert.full_name} — {self.category.code} — {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        rate = type(self)._FX.get(self.currency, Decimal("1"))
        self.amount_usd = (self.amount * rate).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════════
# 4. MONTHLY INVOICES
# ═══════════════════════════════════════════════════════════════

class MonthlyInvoice(models.Model):
    """Consolidated invoice per company per month."""

    company = models.ForeignKey(
        "organization.Company", on_delete=models.PROTECT,
        related_name="monthly_invoices",
    )
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveIntegerField()
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=ExpertCost.Status.choices,
        default=ExpertCost.Status.DRAFT,
    )
    pdf = models.FileField(upload_to="invoices/", null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Monthly Invoice"
        verbose_name_plural = "Monthly Invoices"
        ordering = ["-period_year", "-period_month"]
        unique_together = [("company", "period_year", "period_month")]

    def __str__(self):
        return f"{self.invoice_number} — {self.company.name} — {self.period_month:02d}/{self.period_year}"

    @property
    def period_label(self):
        return f"{self.period_month:02d}/{self.period_year}"


# ═══════════════════════════════════════════════════════════════
# 5. EXPORT LOG — audit trail for every PDF / Excel download
# ═══════════════════════════════════════════════════════════════

class ExportLog(models.Model):
    """Audit trail of every compliance export (PDF / Excel)."""

    class Format(models.TextChoices):
        PDF = "PDF", "PDF"
        EXCEL = "EXCEL", "Excel"
        CSV = "CSV", "CSV"

    user_id = models.IntegerField(null=True, blank=True)
    user_repr = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=10, choices=Format.choices)
    report_type = models.CharField(max_length=60, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    filters = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Export Log"
        verbose_name_plural = "Export Logs"
        indexes = [
            models.Index(fields=["user_id", "created_at"]),
            models.Index(fields=["format", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user_repr} — {self.format} @ {self.created_at:%Y-%m-%d %H:%M}"
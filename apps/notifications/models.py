"""
Notification engine models — configurable alert tiers + send log.

An AlertTier defines WHEN and HOW to notify (e.g., "90 days before" via email).
An AlertLog prevents duplicate sends and records the delivery result.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.experts.models import ExpertProfile


class AlertTier(models.Model):
    """Configurable threshold for sending document-expiry notifications."""

    class Channel(models.TextChoices):
        EMAIL = "EMAIL", _("Email only")
        SMS = "SMS", _("SMS only")
        BOTH = "BOTH", _("Email + SMS")

    class AppliesTo(models.TextChoices):
        ALL = "ALL", _("All document types")
        PASSPORT = "PASSPORT", _("Passports only")
        YELLOW_FEVER = "YELLOW_FEVER", _("Yellow fever cards only")
        CARTE = "CARTE", _("Cartes de Travail only")
        VISA = "VISA", _("Visas only")

    name = models.CharField(
        max_length=100,
        help_text=_("Human-readable label, e.g. 'T-90 warning'."),
    )
    threshold_days = models.PositiveIntegerField(
        db_index=True,
        help_text=_("Days before expiry to trigger (e.g., 90)."),
    )
    channel = models.CharField(
        max_length=10, choices=Channel.choices, default=Channel.EMAIL,
    )
    applies_to = models.CharField(
        max_length=20, choices=AppliesTo.choices, default=AppliesTo.ALL,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-threshold_days", "sort_order"]
        verbose_name = _("Alert Tier")
        verbose_name_plural = _("Alert Tiers")
        unique_together = [("threshold_days", "applies_to")]

    def __str__(self):
        return f"T-{self.threshold_days} {self.applies_to} ({self.channel})"


class AlertLog(models.Model):
    """
    Record of one sent alert. Unique per (expert, doc_type, doc_id, threshold).
    Prevents duplicate sends even if the daily scan runs twice.
    """

    class Status(models.TextChoices):
        SENT = "SENT", _("Sent")
        FAILED = "FAILED", _("Failed")
        SKIPPED = "SKIPPED", _("Skipped")

    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="alerts",
    )
    document_type = models.CharField(max_length=40)
    document_id = models.CharField(max_length=64, blank=True)
    threshold_days = models.PositiveIntegerField(db_index=True)
    channel = models.CharField(max_length=10)
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.SENT,
    )
    error_message = models.TextField(blank=True)
    recipients = models.TextField(
        blank=True, help_text="Comma-separated email/phone list.",
    )

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = _("Alert Log")
        verbose_name_plural = _("Alert Logs")
        unique_together = [
            ("expert", "document_type", "document_id", "threshold_days"),
        ]
        indexes = [
            models.Index(fields=["expert", "document_type"]),
            models.Index(fields=["sent_at", "status"]),
        ]

    def __str__(self):
        return f"{self.expert.full_name} — {self.document_type} T-{self.threshold_days} ({self.status})"
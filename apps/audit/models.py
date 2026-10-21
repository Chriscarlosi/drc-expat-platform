"""
Immutable hash-chained audit log.
SOC 2 / ISO 27001 compliance standard.
"""

from __future__ import annotations

import hashlib
import json

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


GENESIS_HASH = "0" * 64


# ═══════════════════════════════════════════════════════════════
# IMMUTABLE AUDIT LOG
# ═══════════════════════════════════════════════════════════════

class ImmutableAuditLog(models.Model):
    """Append-only hash-chained audit log. Never update. Never delete."""

    class Action(models.TextChoices):
        CREATE = "CREATE", _("Create")
        UPDATE = "UPDATE", _("Update")
        DELETE = "DELETE", _("Delete")
        LOGIN = "LOGIN", _("Login")
        LOGOUT = "LOGOUT", _("Logout")
        ACCESS = "ACCESS", _("Access")
        SYSTEM = "SYSTEM", _("System")

    sequence = models.BigIntegerField(unique=True, editable=False, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True, editable=False)
    user_id = models.IntegerField(null=True, blank=True, editable=False, db_index=True)
    user_repr = models.CharField(max_length=255, blank=True, editable=False)
    action = models.CharField(
        max_length=20, choices=Action.choices,
        db_index=True, editable=False,
    )
    model_name = models.CharField(max_length=100, blank=True, editable=False, db_index=True)
    object_id = models.CharField(max_length=100, blank=True, editable=False)
    object_repr = models.CharField(max_length=500, blank=True, editable=False)
    changes = models.JSONField(default=dict, blank=True, editable=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True, editable=False)
    user_agent = models.CharField(max_length=500, blank=True, editable=False)
    prev_hash = models.CharField(max_length=64, editable=False, db_index=True)
    entry_hash = models.CharField(max_length=64, unique=True, editable=False)
    chain_head = models.BooleanField(default=False, editable=False, db_index=True)

    class Meta:
        ordering = ["-sequence"]
        verbose_name = "Immutable Audit Log Entry"
        verbose_name_plural = "Immutable Audit Log"
        indexes = [
            models.Index(fields=["sequence"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        return (
            f"[{self.sequence}] {self.timestamp:%Y-%m-%d %H:%M} · "
            f"{self.user_repr} · {self.action} {self.model_name}"
        )

    # ─── Append-only guards ────────────────────────────────

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("ImmutableAuditLog entries cannot be modified.")
        last = ImmutableAuditLog.objects.order_by("-sequence").first()
        self.sequence = (last.sequence + 1) if last else 1
        self.prev_hash = last.entry_hash if last else GENESIS_HASH
        if last and last.chain_head:
            ImmutableAuditLog.objects.filter(pk=last.pk).update(chain_head=False)
        self.entry_hash = self._compute_hash()
        self.chain_head = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("ImmutableAuditLog entries cannot be deleted.")

    def _compute_hash(self):
        payload = {
            "sequence": self.sequence,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "user_repr": self.user_repr,
            "action": self.action,
            "model_name": self.model_name,
            "object_id": self.object_id,
            "object_repr": self.object_repr,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "prev_hash": self.prev_hash,
        }
        raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify(self):
        """Recompute the hash and compare. Returns True if the entry is intact."""
        return self._compute_hash() == self.entry_hash


# ═══════════════════════════════════════════════════════════════
# AUDIT CHAIN CHECK — cached result of the last verify run
# ═══════════════════════════════════════════════════════════════

class AuditChainCheck(models.Model):
    """Stores the result of every verify_audit_chain run."""

    checked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_valid = models.BooleanField(default=True)
    entry_count = models.IntegerField(default=0)
    head_hash = models.CharField(max_length=64, blank=True)
    duration_ms = models.IntegerField(default=0)

    class Meta:
        ordering = ["-checked_at"]
        verbose_name = "Audit Chain Check"
        verbose_name_plural = "Audit Chain Checks"

    def __str__(self):
        status = "✓ OK" if self.is_valid else "✗ FAIL"
        return f"{status} @ {self.checked_at:%Y-%m-%d %H:%M}"

    @classmethod
    def latest(cls):
        """Return the most recent verification record."""
        return cls.objects.order_by("-checked_at").first()
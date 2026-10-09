"""
Document versioning — every upload of a file gets preserved with a SHA-256 hash.
Provides a complete, tamper-evident history of every document.
"""

from __future__ import annotations

import hashlib
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from encrypted_model_fields.fields import EncryptedCharField


class DocumentVersion(models.Model):
    """
    One version of one file attached to one parent object.

    Example:
      parent = ExpertProfile #42, field_name = "passport_scan"
      versions = [v1 (2024-01-05), v2 (2025-08-12), v3 (2026-10-09)]
      Only v3 has is_current=True.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ─── Generic parent link ────────────────────────────────
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="document_versions",
    )
    object_id = models.CharField(max_length=64, db_index=True)
    parent = GenericForeignKey("content_type", "object_id")

    # ─── Field & version ────────────────────────────────────
    field_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Name of the FileField on the parent model, e.g. 'passport_scan'.",
    )
    version_number = models.PositiveIntegerField(
        help_text="Auto-increments per (parent, field_name).",
    )
    is_current = models.BooleanField(default=True, db_index=True)

    # ─── File ───────────────────────────────────────────────
    file = models.FileField(upload_to="documents/%Y/%m/")
    original_filename = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.BigIntegerField(default=0)
    content_type_mime = models.CharField(max_length=100, blank=True)

    # ─── Tamper-evidence ────────────────────────────────────
    sha256 = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 of the file bytes when this version was uploaded.",
    )

    # ─── Provenance ─────────────────────────────────────────
    uploaded_by_id = models.IntegerField(null=True, blank=True)
    uploaded_by_repr = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now, db_index=True)
    reason = models.CharField(
        max_length=255, blank=True,
        help_text="Why this version was uploaded (e.g., 'renewal', 'correction').",
    )
    notes = models.TextField(blank=True)

    # ─── Optional metadata (encrypted at rest) ──────────────
    document_number = EncryptedCharField(
        max_length=100, blank=True,
        help_text="Optional: passport number, permit number, etc.",
    )

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Document Version"
        verbose_name_plural = "Document Versions"
        indexes = [
            models.Index(fields=["content_type", "object_id", "field_name"]),
            models.Index(fields=["content_type", "object_id", "field_name", "is_current"]),
            models.Index(fields=["sha256"]),
        ]
        unique_together = [("content_type", "object_id", "field_name", "version_number")]

    def __str__(self):
        return f"{self.field_name} v{self.version_number} — {self.uploaded_by_repr or 'system'}"

    # ─── Immutability guard ─────────────────────────────────

    def save(self, *args, **kwargs):
        if self.pk and DocumentVersion.objects.filter(pk=self.pk).exists():
            # Only allow toggling is_current off (chain flip). Nothing else.
            current = DocumentVersion.objects.get(pk=self.pk)
            if (
                current.file != self.file
                or current.sha256 != self.sha256
                or current.version_number != self.version_number
            ):
                raise ValueError(
                    "DocumentVersion entries are immutable. "
                    "Upload a new version instead of editing this one."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError(
            "DocumentVersion entries are immutable. "
            "Set is_current=False or upload a corrective version."
        )

    # ─── Hash helper ────────────────────────────────────────

    @staticmethod
    def compute_sha256(file_field) -> str:
        """Compute the SHA-256 of an uploaded file."""
        file_field.seek(0)
        hasher = hashlib.sha256()
        for chunk in iter(lambda: file_field.read(8192), b""):
            hasher.update(chunk)
        file_field.seek(0)
        return hasher.hexdigest()

    def verify_integrity(self) -> bool:
        """Recompute the SHA-256 of the current file and compare."""
        try:
            self.file.seek(0)
            return self.compute_sha256(self.file) == self.sha256
        except Exception:
            return False
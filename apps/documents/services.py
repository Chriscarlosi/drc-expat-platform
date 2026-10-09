"""
DocumentVersion service — the ONLY entry point for creating versions.
Views, signals, and admin should call these methods, never touch the model directly.
"""

from __future__ import annotations

import logging

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import DocumentVersion

logger = logging.getLogger(__name__)


class DocumentVersionService:
    """Handles versioning for any FileField on any model."""

    @classmethod
    @transaction.atomic
    def capture(
        cls,
        *,
        parent,
        field_name: str,
        file_obj,
        user=None,
        reason: str = "",
        notes: str = "",
        document_number: str = "",
    ) -> DocumentVersion:
        """
        Capture a new version of `parent.field_name`.
        Flip all previous versions of the same field to is_current=False.
        """
        if file_obj is None:
            raise ValueError("file_obj is required")

        ct = ContentType.objects.get_for_model(parent)
        object_id = str(parent.pk)

        # Lock existing versions of this exact field
        existing = DocumentVersion.objects.select_for_update().filter(
            content_type=ct, object_id=object_id, field_name=field_name,
        )
        next_version = existing.count() + 1

        # Flip current off
        existing.filter(is_current=True).update(is_current=False)

        sha = DocumentVersion.compute_sha256(file_obj)
        size = getattr(file_obj, "size", 0) or 0
        original = getattr(file_obj, "name", "")[:255]

        version = DocumentVersion.objects.create(
            content_type=ct,
            object_id=object_id,
            field_name=field_name,
            version_number=next_version,
            is_current=True,
            file=file_obj,
            original_filename=original,
            file_size_bytes=size,
            sha256=sha,
            uploaded_by_id=getattr(user, "id", None) if user else None,
            uploaded_by_repr=str(user) if user else "system",
            uploaded_at=timezone.now(),
            reason=reason[:255],
            notes=notes,
            document_number=document_number,
        )

        logger.info(
            "Document version captured",
            extra={
                "parent": f"{ct.app_label}.{ct.model}:{object_id}",
                "field": field_name,
                "version": next_version,
                "sha256": sha,
            },
        )
        return version

    @classmethod
    def history(cls, *, parent, field_name: str):
        """All versions of one field on one object, newest first."""
        ct = ContentType.objects.get_for_model(parent)
        return DocumentVersion.objects.filter(
            content_type=ct,
            object_id=str(parent.pk),
            field_name=field_name,
        ).order_by("-version_number")

    @classmethod
    def current(cls, *, parent, field_name: str):
        ct = ContentType.objects.get_for_model(parent)
        return DocumentVersion.objects.filter(
            content_type=ct,
            object_id=str(parent.pk),
            field_name=field_name,
            is_current=True,
        ).first()
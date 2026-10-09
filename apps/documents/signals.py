"""
Auto-capture document versions when FileFields on tracked models change.

Compares the incoming file against the last stored version. If different
(by size or name), captures a new version. No markers needed.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# (app_label.ModelName, field_name)
TRACKED_FIELDS = [
    ("experts.ExpertProfile", "passport_scan"),
    ("experts.ExpertProfile", "yellow_fever_scan"),
    ("visas.CarteDeTravail", "scan"),
    ("visas.FlyingVisa", "dgm_authorization_scan"),
    ("visas.AirportVisa", "dgm_authorization_scan"),
    ("visas.VoyageVisa", "dgm_authorization_scan"),
    ("visas.EstablishmentVisa", "dgm_authorization_scan"),
    ("visas.VisaRecord", "dgm_authorization_scan"),
    ("visas.VisaProlongation", "scan"),
    ("compliance.ExpertCost", "receipt"),
    ("compliance.MonthlyInvoice", "pdf"),
]


def _register_tracked_signals():
    from django.apps import apps as django_apps

    for label, field_name in TRACKED_FIELDS:
        try:
            model = django_apps.get_model(label)
        except LookupError:
            logger.warning(f"Document versioning: model {label} not found")
            continue
        _attach(model, field_name)


def _attach(model, field_name):
    @receiver(
        post_save,
        sender=model,
        dispatch_uid=f"docver_{model._meta.label}_{field_name}",
    )
    def _capture(sender, instance, created, **kwargs):
        file_obj = getattr(instance, field_name, None)
        if not file_obj or not getattr(file_obj, "name", None):
            return

        from .services import DocumentVersionService
        from .models import DocumentVersion
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(instance)
        existing = DocumentVersion.objects.filter(
            content_type=ct,
            object_id=str(instance.pk),
            field_name=field_name,
            is_current=True,
        ).first()

        # If a current version exists with the same filename and size, skip
        if existing:
            same_name = existing.original_filename == file_obj.name[:255]
            same_size = existing.file_size_bytes == getattr(file_obj, "size", 0)
            if same_name and same_size:
                return

        try:
            DocumentVersionService.capture(
                parent=instance,
                field_name=field_name,
                file_obj=file_obj,
                user=getattr(instance, "_current_user", None),
                reason="Auto-captured on save",
            )
        except Exception as e:
            logger.exception(f"Document versioning capture failed: {e}")


# Auto-register when Django is ready
_register_tracked_signals()
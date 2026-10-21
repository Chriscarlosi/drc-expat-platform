"""Bridge django-auditlog → ImmutableAuditLog with recursion guard."""

from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from auditlog.models import LogEntry as DjangoAuditLogEntry

from .models import ImmutableAuditLog
from .current_user import get_current_user


logger = logging.getLogger(__name__)

_ACTION_MAP = {
    0: ImmutableAuditLog.Action.CREATE,
    1: ImmutableAuditLog.Action.UPDATE,
    2: ImmutableAuditLog.Action.DELETE,
    3: ImmutableAuditLog.Action.ACCESS,
}

_SKIP_MODELS = {"immutableauditlog", "logentry"}


@receiver(post_save, sender=DjangoAuditLogEntry)
def chain_django_audit_entry(sender, instance, created, **kwargs):
    if not created:
        return

    model_name = (
        instance.content_type.model if instance.content_type else ""
    ).lower()

    if model_name in _SKIP_MODELS:
        return

    action = _ACTION_MAP.get(instance.action, ImmutableAuditLog.Action.SYSTEM)

    # ── Actor resolution (in order of priority) ─────────
    #  1. Explicit actor on the LogEntry (set by django-auditlog when possible)
    #  2. Current request user (from contextvar set by middleware)
    #  3. Fallback: "system"
    user_id = instance.actor_id
    user_repr = str(instance.actor) if instance.actor else None

    if user_repr is None:
        current = get_current_user()
        if current and getattr(current, "is_authenticated", False):
            user_id = getattr(current, "id", None)
            user_repr = (
                getattr(current, "get_full_name", lambda: "")() or
                getattr(current, "username", "unknown")
            )

    ImmutableAuditLog.objects.create(
        timestamp=instance.timestamp,
        user_id=user_id,
        user_repr=user_repr or "system",
        action=action,
        model_name=model_name,
        object_id=str(instance.object_id or ""),
        object_repr=(instance.object_repr or "")[:500],
        changes=instance.changes or {},
        ip_address=getattr(instance, "remote_addr", None),
        user_agent="",
    )
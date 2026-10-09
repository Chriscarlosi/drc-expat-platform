"""Bridge django-auditlog → ImmutableAuditLog with recursion guard."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from auditlog.models import LogEntry as DjangoAuditLogEntry

from .models import ImmutableAuditLog


_ACTION_MAP = {
    0: ImmutableAuditLog.Action.CREATE,
    1: ImmutableAuditLog.Action.UPDATE,
    2: ImmutableAuditLog.Action.DELETE,
    3: ImmutableAuditLog.Action.ACCESS,
}

# Models that must NEVER be chained (to prevent recursion)
_SKIP_MODELS = {"immutableauditlog", "logentry"}


@receiver(post_save, sender=DjangoAuditLogEntry)
def chain_django_audit_entry(sender, instance, created, **kwargs):
    if not created:
        return

    # ─── RECURSION GUARD ───────────────────────────────────
    # If this LogEntry is about our own audit tables, skip it.
    model_name = (
        instance.content_type.model
        if instance.content_type else ""
    ).lower()
    if model_name in _SKIP_MODELS:
        return

    action = _ACTION_MAP.get(instance.action, ImmutableAuditLog.Action.SYSTEM)

    ImmutableAuditLog.objects.create(
        timestamp=instance.timestamp,
        user_id=instance.actor_id,
        user_repr=str(instance.actor) if instance.actor else "system",
        action=action,
        model_name=model_name,
        object_id=str(instance.object_id or ""),
        object_repr=(instance.object_repr or "")[:500],
        changes=instance.changes or {},
        ip_address=getattr(instance, "remote_addr", None),
        user_agent="",
    )
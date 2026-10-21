"""
Notification Engine — reads configurable AlertTiers and fires email/SMS.

Runs daily via Celery Beat. Skips anything already logged in AlertLog
for that (expert, document, threshold) — idempotent.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.experts.models import ExpertProfile
from apps.visas.models import CarteDeTravail
from .models import AlertTier, AlertLog
from .providers import send_email, send_sms

logger = logging.getLogger(__name__)


def _subject_en_fr(*, days_left: int, doc_name: str) -> tuple[str, str]:
    subject = (
        f"[DRC Expat Platform] ALERT: {doc_name} expires in {days_left} days "
        f"/ ALERTE : {doc_name} expire dans {days_left} jours"
    )
    body = (
        f"═══════════════════════════════════════════════════════════\n"
        f"  DRC EXPAT EXPERT & VISA COMPLIANCE PLATFORM\n"
        f"  PLATEFORME DE CONFORMITÉ DRC EXPAT\n"
        f"═══════════════════════════════════════════════════════════\n\n"
        f"⚠️  EXPIRY ALERT — T-{days_left} DAYS\n"
        f"⚠️  ALERTE D'EXPIRATION — T-{days_left} JOURS\n\n"
        f"DOCUMENT / DOCUMENT :\n"
        f"    • {doc_name}\n"
        f"    • Expires / Expire le : {days_left} days / jours\n\n"
        f"ACTION REQUIRED — Contact your HR / Compliance Manager immediately.\n"
        f"ACTION REQUISE — Contactez immédiatement votre responsable RH.\n\n"
        f"═══════════════════════════════════════════════════════════\n"
        f"Automated message. Do not reply. / Message automatique.\n"
        f"═══════════════════════════════════════════════════════════\n"
    )
    return subject, body


def _iter_documents():
    """Yield (expert, doc_type, doc_id, doc_name, expiry_date, doc_number) tuples."""
    expert_mgr = ExpertProfile.objects
    if hasattr(expert_mgr, "unscoped"):
        expert_mgr = expert_mgr.unscoped()

    for e in expert_mgr.filter(is_active=True):
        # Passport
        if e.passport_expiry_date:
            yield (e, "PASSPORT", str(e.id), "Passport / Passeport",
                   e.passport_expiry_date, e.passport_number or "")
        # Yellow fever
        if e.yellow_fever_expiry_date:
            yield (e, "YELLOW_FEVER", str(e.id), "Yellow Fever Card / Carte de Fièvre Jaune",
                   e.yellow_fever_expiry_date, e.yellow_fever_card_number or "")

    # Cartes
    carte_mgr = CarteDeTravail.objects
    if hasattr(carte_mgr, "unscoped"):
        carte_mgr = carte_mgr.unscoped()
    for c in carte_mgr.filter(is_active=True):
        yield (c.expert, "CARTE", str(c.id),
               f"Carte de Travail ({c.permit_number})",
               c.expiry_date, c.permit_number or "")

    # Visas
    from apps.visas.models import (
        FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa,
    )
    for model in [FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa]:
        mgr = model.objects
        if hasattr(mgr, "unscoped"):
            mgr = mgr.unscoped()
        for v in mgr.exclude(status__in=["CANCELLED", "EXPIRED"]):
            yield (v.expert, "VISA", str(v.id),
                   str(model._meta.verbose_name), v.expiry_date,
                   getattr(v, "visa_number", "") or "")


def _already_sent(*, expert_id, doc_type: str, doc_id: str, threshold: int) -> bool:
    return AlertLog.objects.filter(
        expert_id=expert_id,
        document_type=doc_type,
        document_id=doc_id,
        threshold_days=threshold,
        status=AlertLog.Status.SENT,
    ).exists()


@shared_task(name="notifications.check_document_expirations")
def check_document_expirations():
    """Daily scan — iterate every active AlertTier, send per its config."""
    today = timezone.now().date()
    tiers = AlertTier.objects.filter(is_active=True)

    sent_total = 0
    skipped_total = 0
    failed_total = 0

    # Cache documents once
    docs = list(_iter_documents())
    logger.info("Scan: %d tiers, %d documents", tiers.count(), len(docs))

    for tier in tiers:
        for expert, doc_type, doc_id, doc_name, expiry, doc_number in docs:
            # Category filter
            if tier.applies_to != AlertTier.AppliesTo.ALL:
                if tier.applies_to != doc_type:
                    continue

            days_left = (expiry - today).days
            if days_left != tier.threshold_days:
                continue

            # Idempotency: skip if already sent
            if _already_sent(
                expert_id=expert.id, doc_type=doc_type,
                doc_id=doc_id, threshold=tier.threshold_days,
            ):
                skipped_total += 1
                continue

            subject, body = _subject_en_fr(days_left=days_left, doc_name=doc_name)

            recipients_email = []
            recipients_sms = []
            if expert.email:
                recipients_email.append(expert.email)
            if expert.phone:
                recipients_sms.append(expert.phone)

            status = AlertLog.Status.SENT
            error_msg = ""
            recipients_str = ""

            # Email
            if tier.channel in (AlertTier.Channel.EMAIL, AlertTier.Channel.BOTH):
                ok, err = send_email(
                    subject=subject, body=body, recipients=recipients_email,
                )
                if not ok:
                    status = AlertLog.Status.FAILED
                    error_msg += f"EMAIL: {err}; "
                recipients_str += ",".join(recipients_email)

            # SMS
            if tier.channel in (AlertTier.Channel.SMS, AlertTier.Channel.BOTH):
                sms_body = f"DRC Expat: {doc_name} expires in {days_left}d. Contact HR."
                for phone in recipients_sms:
                    ok, err = send_sms(phone=phone, body=sms_body)
                    if not ok:
                        status = AlertLog.Status.FAILED
                        error_msg += f"SMS[{phone}]: {err}; "
                recipients_str += ("," + ",".join(recipients_sms) if recipients_sms else "")

            AlertLog.objects.create(
                expert=expert,
                document_type=doc_type,
                document_id=doc_id,
                threshold_days=tier.threshold_days,
                channel=tier.channel,
                status=status,
                error_message=error_msg,
                recipients=recipients_str.strip(","),
            )
            if status == AlertLog.Status.SENT:
                sent_total += 1
            else:
                failed_total += 1

    return (
        f"Scan complete. Sent={sent_total}, Skipped(dup)={skipped_total}, "
        f"Failed={failed_total}, Tiers={tiers.count()}"
    )
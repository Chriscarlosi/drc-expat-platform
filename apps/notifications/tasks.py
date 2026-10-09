"""
Notification Engine — automated T-90/T-60/T-30 expiry alerts (bilingual EN/FR).
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from apps.experts.models import ExpertProfile
from apps.visas.models import (
    CarteDeTravail, FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa,
)

THRESHOLDS = [90, 60, 30]


def _send_bilingual_alert(expert, doc_name_en, doc_name_fr, doc_expiry, days_left):
    """Send a bilingual expiry warning to the expert and HR."""
    subject = (
        f"[DRC Expat Platform] ALERT: {doc_name_en} expires in {days_left} days "
        f"/ ALERTE : {doc_name_fr} expire dans {days_left} jours"
    )

    message = f"""
════════════════════════════════════════════════════════════
  DRC EXPAT EXPERT & VISA COMPLIANCE PLATFORM
  PLATEFORME DE CONFORMITÉ DRC EXPAT
════════════════════════════════════════════════════════════

⚠️  EXPIRY ALERT — T-{days_left} DAYS
⚠️  ALERTE D'EXPIRATION — T-{days_left} JOURS

Dear {expert.first_name} {expert.last_name},

This is an automated compliance notification from the DRC Expat Platform.

DOCUMENT EXPIRING SOON:
    • Document    : {doc_name_en}
    • Expiry Date : {doc_expiry}
    • Days Left   : {days_left}

ACTION REQUIRED:
Please contact your HR / Compliance Manager immediately to initiate
the renewal or extension process with the relevant authority (DGM,
Ministry of Labour).

────────────────────────────────────────────────────────────

Cher/Chère {expert.first_name} {expert.last_name},

Ceci est une notification de conformité automatique de la Plateforme
DRC Expat.

DOCUMENT EXPIRE BIENTÔT :
    • Document         : {doc_name_fr}
    • Date d'expiration: {doc_expiry}
    • Jours restants   : {days_left}

ACTION REQUISE :
Veuillez contacter immédiatement votre responsable RH / Conformité
pour lancer le processus de renouvellement ou de prolongation auprès
de l'autorité compétente (DGM, Ministère du Travail).

════════════════════════════════════════════════════════════
This is an automated message. Do not reply.
Ceci est un message automatique. Ne pas répondre.
════════════════════════════════════════════════════════════
"""

    recipients = [expert.email]
    # Add HR manager emails when multi-tenant is implemented
    # e.g., recipients.append(expert.employer_company.hr_email)

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )


@shared_task(name='notifications.check_document_expirations')
def check_document_expirations():
    """
    Daily scan of all expert documents for T-90/T-60/T-30 expiry.
    Runs via Celery Beat once per day.
    """
    today = timezone.now().date()
    alerts_sent = 0

    # ─── 1. Expert Profiles — Passport & Yellow Fever ────────
    for expert in ExpertProfile.objects.filter(is_active=True):
        if expert.passport_expiry_date:
            days_left = (expert.passport_expiry_date - today).days
            if days_left in THRESHOLDS:
                _send_bilingual_alert(
                    expert, 'Passport', 'Passeport',
                    expert.passport_expiry_date, days_left,
                )
                alerts_sent += 1

        if expert.yellow_fever_expiry_date:
            days_left = (expert.yellow_fever_expiry_date - today).days
            if days_left in THRESHOLDS:
                _send_bilingual_alert(
                    expert, 'Yellow Fever Card', 'Carte de Fièvre Jaune',
                    expert.yellow_fever_expiry_date, days_left,
                )
                alerts_sent += 1

    # ─── 2. Cartes de Travail (Ministry of Labour) ───────────
    for permit in CarteDeTravail.objects.filter(is_active=True):
        days_left = (permit.expiry_date - today).days
        if days_left in THRESHOLDS:
            _send_bilingual_alert(
                permit.expert,
                f"Carte de Travail ({permit.permit_number})",
                f"Carte de Travail ({permit.permit_number})",
                permit.expiry_date, days_left,
            )
            alerts_sent += 1

    # ─── 3. All Visa Types ───────────────────────────────────
    visa_models = [FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa]
    for model in visa_models:
        visas = model.objects.filter(status__in=['ACTIVE', 'EXPIRING_SOON'])
        for visa in visas:
            days_left = (visa.expiry_date - today).days
            if days_left in THRESHOLDS:
                _send_bilingual_alert(
                    visa.expert,
                    model._meta.verbose_name,
                    model._meta.verbose_name,
                    visa.expiry_date, days_left,
                )
                alerts_sent += 1

    return f"Expiry scan complete. {alerts_sent} alert(s) sent."
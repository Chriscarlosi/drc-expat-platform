import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import VisaRecord
from apps.audit.models import ImmutableAuditLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def daily_visa_expiry_check(self):
    """
    Daily task to update statuses and send email alerts for T-90, T-60, T-30.
    Idempotent: Checks the audit log to avoid sending the same alert twice in a week.
    """
    try:
        today = timezone.now().date()
        t30 = today + timedelta(days=30)
        t60 = today + timedelta(days=60)
        t90 = today + timedelta(days=90)

        # 1. Update EXPIRED visas
        expired_visas = VisaRecord.objects.filter(
            expiry_date__lt=today,
            status__in=[VisaRecord.Status.ACTIVE, VisaRecord.Status.EXPIRING_SOON]
        )
        expired_count = expired_visas.update(status=VisaRecord.Status.EXPIRED)

        # 2. Update EXPIRING_SOON visas
        expiring_soon_visas = VisaRecord.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=t90,
            status=VisaRecord.Status.ACTIVE
        )
        expiring_soon_count = expiring_soon_visas.update(status=VisaRecord.Status.EXPIRING_SOON)

        # 3. Send Alerts (T-90, T-60, T-30)
        alert_count = 0
        visas_to_alert = VisaRecord.objects.filter(
            expiry_date__gte=today,
            expiry_date__lte=t90,
            status__in=[VisaRecord.Status.ACTIVE, VisaRecord.Status.EXPIRING_SOON]
        ).select_related('expert', 'visa_type')

        for visa in visas_to_alert:
            days_left = (visa.expiry_date - today).days

            # Determine threshold tier
            if days_left <= 30:
                tier = "T-30 CRITICAL"
            elif days_left <= 60:
                tier = "T-60 URGENT"
            else:
                tier = "T-90 WARNING"

            # Idempotency Check: Has this specific alert been sent in the last 7 days?
            seven_days_ago = timezone.now() - timedelta(days=7)
            recent_alert = ImmutableAuditLog.objects.filter(
                action="ALERT_SENT",
                object_repr=f"Visa {visa.visa_number} ({tier})",
                timestamp__gte=seven_days_ago
            ).exists()

            if not recent_alert:
                # Prepare Email
                subject = f"[{tier}] Visa Expiry Alert: {visa.expert.full_name} ({days_left} days left)"
                message = (
                    f"COMPLIANCE ALERT from DRC Expat Platform\n\n"
                    f"Expert: {visa.expert.full_name}\n"
                    f"Visa Type: {visa.visa_type.code} - {visa.visa_type.name_en}\n"
                    f"Visa Number: {visa.visa_number}\n"
                    f"Expiry Date: {visa.expiry_date}\n"
                    f"Days Remaining: {days_left}\n\n"
                    f"Please log into the platform to initiate a prolongation or renewal request immediately.\n"
                )

                recipient = visa.expert.email if visa.expert.email else settings.DEFAULT_FROM_EMAIL

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient],
                    fail_silently=False,
                )

                # Log the alert in the immutable audit log (using correct fields)
                ImmutableAuditLog.objects.create(
                    user_repr="System (Celery Task)",
                    action="ALERT_SENT",
                    model_name="VisaRecord",
                    object_repr=f"Visa {visa.visa_number} ({tier})",
                    changes={"info": f"Sent {tier} email alert to {recipient}."}
                )

                alert_count += 1
                logger.info(f"Sent {tier} alert for {visa.visa_number} to {recipient}")

        return f"Updated {expired_count} expired, {expiring_soon_count} expiring soon. Sent {alert_count} alerts."

    except Exception as exc:
        logger.error(f"Error in daily_visa_expiry_check: {exc}")
        raise self.retry(exc=exc)
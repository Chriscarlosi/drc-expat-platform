"""
Notification providers — Email + SMS.

SMS uses Africa's Talking (Africa-focused) by default, with a console fallback
when credentials aren't configured. To enable real SMS:
  1. Sign up at https://africastalking.com
  2. Set env vars: SMS_PROVIDER=africastalking, AT_USERNAME, AT_API_KEY, AT_SENDER_ID
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# EMAIL
# ═══════════════════════════════════════════════════════════════

def send_email(*, subject: str, body: str, recipients: list[str]) -> tuple[bool, str]:
    """Send email. Returns (success, error_message)."""
    if not recipients:
        return False, "No recipients"
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        return True, ""
    except Exception as e:
        logger.exception("Email send failed")
        return False, str(e)


# ═══════════════════════════════════════════════════════════════
# SMS
# ═══════════════════════════════════════════════════════════════

def _send_sms_console(phone: str, body: str) -> tuple[bool, str]:
    """Dev fallback — print to terminal."""
    print(f"\n[SMS → {phone}]\n{body}\n")
    return True, ""


def _send_sms_africastalking(phone: str, body: str) -> tuple[bool, str]:
    try:
        import africastalking
        africastalking.initialize(
            username=getattr(settings, "AT_USERNAME", ""),
            api_key=getattr(settings, "AT_API_KEY", ""),
        )
        sms = africastalking.SMS
        sender = getattr(settings, "AT_SENDER_ID", None)
        kwargs = {"sender_id": sender} if sender else {}
        response = sms.send(body, [phone], **kwargs)
        logger.info("SMS sent to %s: %s", phone, response)
        return True, ""
    except Exception as e:
        logger.exception("Africa's Talking SMS failed")
        return False, str(e)


def send_sms(*, phone: str, body: str) -> tuple[bool, str]:
    """Send SMS. Returns (success, error_message)."""
    if not phone:
        return False, "No phone number"

    provider = getattr(settings, "SMS_PROVIDER", "console")

    if provider == "africastalking":
        return _send_sms_africastalking(phone, body)
    return _send_sms_console(phone, body)
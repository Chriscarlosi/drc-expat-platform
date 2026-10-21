import logging
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from .models import VisaRecord, VisaProlongation, VisaTypeCatalog

logger = logging.getLogger(__name__)


def calculate_visa_expiry(issue_date, validity_months):
    """Ticket 1: Standardized expiry calculation."""
    if not issue_date or not validity_months:
        return None
    return issue_date + relativedelta(months=validity_months)


def validate_visa_validity(visa_record):
    """Ticket 1: Enforce visa validity rules with tolerance."""
    catalog = visa_record.visa_type
    if not catalog.validity_months or not visa_record.issue_date:
        return

    expected_expiry = calculate_visa_expiry(visa_record.issue_date, catalog.validity_months)
    tolerance = getattr(settings, 'VISA_EXPIRY_TOLERANCE_DAYS', 5)

    if visa_record.expiry_date:
        delta = abs((visa_record.expiry_date - expected_expiry).days)
        if delta > tolerance:
            raise ValidationError(
                f"Expiry date {visa_record.expiry_date} does not match the allowed validity "
                f"of {catalog.validity_months} months (expected around {expected_expiry})."
            )
    else:
        visa_record.expiry_date = expected_expiry


def validate_carte_de_travail(visa_record):
    """Ticket 2: Carte de travail requirement blocks activation."""
    if visa_record.status == VisaRecord.Status.ACTIVE and visa_record.visa_type.requires_carte_de_travail:
        # Check if there's an associated carte de travail (via legacy EstablishmentVisa for now, or add a FK)
        # Assuming we add a direct FK later, for now we check the expert's permits.
        from .models import CarteDeTravail
        has_valid_permit = CarteDeTravail.objects.filter(
            expert=visa_record.expert,
            is_active=True,
            expiry_date__gte=visa_record.expiry_date
        ).exists()

        if not has_valid_permit:
            raise ValidationError(
                f"Visa type {visa_record.visa_type.code} requires a valid Carte de Travail "
                "that extends beyond the visa's expiry date."
            )


def compute_visa_status(visa_record):
    """Ticket 3: Computed visa status (Daily expiry logic helper)."""
    if visa_record.status in [VisaRecord.Status.CANCELLED, VisaRecord.Status.TRANSFERRED]:
        return visa_record.status

    today = timezone.now().date()
    if visa_record.expiry_date < today:
        return VisaRecord.Status.EXPIRED
    elif visa_record.days_until_expiry <= 90:
        return VisaRecord.Status.EXPIRING_SOON
    return VisaRecord.Status.ACTIVE


@transaction.atomic
def approve_prolongation(prolongation_id, user):
    """Ticket 9: Approval service (single transaction, keep history)."""
    prolongation = VisaProlongation.objects.select_for_update().get(id=prolongation_id)

    if prolongation.status == VisaProlongation.Status.APPROVED:
        raise ValidationError("This prolongation is already approved.")

    # Ticket 10: Unique DGM reference check
    if prolongation.dgm_reference and VisaProlongation.objects.filter(
            dgm_reference=prolongation.dgm_reference
    ).exclude(id=prolongation.id).exists():
        raise ValidationError(f"DGM Reference {prolongation.dgm_reference} is already in use.")

    parent_visa = VisaRecord.objects.select_for_update().get(id=prolongation.parent_visa.id)

    prolongation.old_expiry_date = parent_visa.expiry_date
    parent_visa.expiry_date = prolongation.new_expiry_date
    parent_visa.save()

    prolongation.status = VisaProlongation.Status.APPROVED
    prolongation.approved_by = user
    prolongation.approval_date = timezone.now().date()
    prolongation.save()

    logger.info(
        f"Prolongation {prolongation.id} approved by {user}. Parent visa {parent_visa.id} extended to {parent_visa.expiry_date}.")
    return prolongation
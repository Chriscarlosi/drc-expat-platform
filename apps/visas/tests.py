from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from apps.experts.models import ExpertProfile
from apps.organization.models import Company
from .models import VisaTypeCatalog, VisaRecord, VisaProlongation
from . import services


class VisaEngineTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Corp")
        self.expert = ExpertProfile.objects.create(
            first_name="John", last_name="Doe",
            date_of_birth=date(1980, 1, 1), gender="M",
            nationality="American", passport_number="P123",
            passport_issue_date=date(2020, 1, 1),
            passport_expiry_date=date(2030, 1, 1),
            employer_company="Test Corp", job_title="Engineer",
            email="john@test.com", company=self.company
        )

        self.vet_visa = VisaTypeCatalog.objects.create(
            code="VET", category="ESTABLISHMENT", name_en="Work", name_fr="Travail",
            validity_months=24, allows_prolongation=True, max_prolongations=1
        )
        self.evets_visa = VisaTypeCatalog.objects.create(
            code="E-VETS", category="ELECTRONIC", name_en="E-Visa", name_fr="E-Visa",
            validity_months=1, allows_prolongation=False, must_exit_on_expiry=True
        )

    def test_validity_rules(self):
        # Should pass (24 months)
        visa = VisaRecord(
            expert=self.expert, visa_type=self.vet_visa,
            visa_number="V1", issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 1, 1) + relativedelta(months=24)
        )
        visa.full_clean()  # Should not raise

        # Should fail (Wrong expiry)
        visa.expiry_date = date(2026, 1, 1) + relativedelta(months=12)
        with self.assertRaises(ValidationError):
            visa.full_clean()

    def test_prolongation_limits(self):
        parent_visa = VisaRecord.objects.create(
            expert=self.expert, visa_type=self.vet_visa,
            visa_number="V2", issue_date=date(2026, 1, 1),
            expiry_date=date(2026, 1, 1) + relativedelta(months=24),
            status=VisaRecord.Status.ACTIVE
        )

        # First prolongation should be fine
        p1 = VisaProlongation(
            expert=self.expert, parent_visa=parent_visa,
            prolongation_type=self.vet_visa,  # Assuming VET allows prolong
            prolongation_number="P1", request_date=date(2026, 6, 1),
            new_expiry_date=date(2028, 1, 1), status=VisaProlongation.Status.REQUESTED
        )
        p1.full_clean()

        # Approve it
        p1.status = VisaProlongation.Status.APPROVED
        p1.save()

        # Second prolongation should fail (max_prolongations=1)
        p2 = VisaProlongation(
            expert=self.expert, parent_visa=parent_visa,
            prolongation_type=self.vet_visa,
            prolongation_number="P2", request_date=date(2026, 7, 1),
            new_expiry_date=date(2028, 7, 1), status=VisaProlongation.Status.REQUESTED
        )
        with self.assertRaises(ValidationError):
            p2.full_clean()
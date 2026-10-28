"""
Automated tests for the Visa Engine.
Run: python manage.py test apps.visas
"""

from datetime import date, timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.experts.models import ExpertProfile
from apps.visas.models import (
    EstablishmentVisa, CarteDeTravail, VisaTypeCatalog
)


class VisaValidityRulesTest(TestCase):
    """Test that visa validity windows are strictly enforced."""

    def setUp(self):
        self.today = timezone.now().date()
        self.expert = ExpertProfile.objects.unscoped().create(
            company=None,  # Assuming null is allowed for testing
            first_name="Test", last_name="Expert",
            date_of_birth="1990-01-01", gender="M",
            nationality="French", is_expatriate=True,
            passport_number="TEST-VALID-001",
            passport_issue_date=self.today - timedelta(days=1000),
            passport_expiry_date=self.today + timedelta(days=1000),
            email="test@kibali.local",
            employer_company="Kibali", job_title="Engineer"
        )

    def test_work_visa_validity_window(self):
        """Work Visa must be 1 to 2 years (365 to 731 days)."""

        # 1. Too Short (100 days) - Should fail
        visa_short = EstablishmentVisa(
            expert=self.expert,
            visa_number="VISA-SHORT",
            issue_date=self.today,
            expiry_date=self.today + timedelta(days=100),
            establishment_type=EstablishmentVisa.EstablishmentType.WORK
        )
        with self.assertRaises(ValidationError):
            visa_short.full_clean()

        # 2. Too Long (800 days) - Should fail
        visa_long = EstablishmentVisa(
            expert=self.expert,
            visa_number="VISA-LONG",
            issue_date=self.today,
            expiry_date=self.today + timedelta(days=800),
            establishment_type=EstablishmentVisa.EstablishmentType.WORK
        )
        with self.assertRaises(ValidationError):
            visa_long.full_clean()

        # 3. Valid (500 days) - Should pass
        visa_valid = EstablishmentVisa(
            expert=self.expert,
            visa_number="VISA-VALID",
            issue_date=self.today,
            expiry_date=self.today + timedelta(days=500),
            establishment_type=EstablishmentVisa.EstablishmentType.WORK
        )
        try:
            visa_valid.full_clean()
        except ValidationError:
            self.fail("Valid Work Visa (500 days) failed validation.")


class CrossMinistryDependencyTest(TestCase):
    """Test that Work Visas require a valid Carte de Travail."""

    def setUp(self):
        self.today = timezone.now().date()
        self.expert = ExpertProfile.objects.unscoped().create(
            company=None,
            first_name="Test", last_name="Expert",
            date_of_birth="1990-01-01", gender="M",
            nationality="French", is_expatriate=True,
            passport_number="TEST-VALID-002",
            passport_issue_date=self.today - timedelta(days=1000),
            passport_expiry_date=self.today + timedelta(days=1000),
            email="test2@kibali.local",
            employer_company="Kibali", job_title="Engineer"
        )

    def test_work_visa_requires_carte_de_travail(self):
        """A Work Visa cannot be ACTIVE without a Carte de Travail."""

        visa = EstablishmentVisa(
            expert=self.expert,
            visa_number="VISA-CROSS-001",
            issue_date=self.today,
            expiry_date=self.today + timedelta(days=400),
            establishment_type=EstablishmentVisa.EstablishmentType.WORK,
            status=EstablishmentVisa.Status.ACTIVE,
            carte_de_travail=None  # MISSING!
        )

        with self.assertRaises(ValidationError) as context:
            visa.full_clean()

        self.assertIn("cannot be Active without a valid Carte", str(context.exception))

    def test_carte_must_cover_visa_duration(self):
        """The Carte de Travail must expire AFTER the visa."""

        # Carte expires in 200 days (BEFORE the visa's 400 days)
        carte = CarteDeTravail.objects.create(
            expert=self.expert,
            permit_number="CARTE-SHORT",
            issue_date=self.today,
            expiry_date=self.today + timedelta(days=200)
        )

        visa = EstablishmentVisa(
            expert=self.expert,
            visa_number="VISA-CROSS-002",
            issue_date=self.today,
            expiry_date=self.today + timedelta(days=400),
            establishment_type=EstablishmentVisa.EstablishmentType.WORK,
            status=EstablishmentVisa.Status.ACTIVE,
            carte_de_travail=carte
        )

        with self.assertRaises(ValidationError) as context:
            visa.full_clean()

        self.assertIn("Carte de Travail expires", str(context.exception))
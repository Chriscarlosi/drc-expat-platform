"""
Automated tests for the Quota Engine.
Run: python manage.py test apps.compliance
"""

from django.test import TestCase
from apps.organization.models import Company
from apps.experts.models import ExpertProfile
from apps.compliance.services.quota_service import QuotaService
from datetime import date, timedelta


class QuotaEngineTest(TestCase):
    """Test the 6.5% expatriate quota math."""

    def setUp(self):
        # Create a company with 5000 Congolese staff
        self.company = Company.objects.create(
            name="Test Mine", slug="test-mine",
            congolese_staff_count=5000
        )
        self.today = date.today()

    def _create_expat(self, index):
        return ExpertProfile.objects.unscoped().create(
            company=self.company,
            first_name=f"Expat{index}", last_name="Test",
            date_of_birth="1990-01-01", gender="M",
            nationality="French", is_expatriate=True,
            passport_number=f"TEST-QUOTA-{index}",
            passport_issue_date=self.today - timedelta(days=1000),
            passport_expiry_date=self.today + timedelta(days=1000),
            email=f"expat{index}@test.local",
            employer_company="Test Mine", job_title="Engineer"
        )

    def test_quota_is_compliant_under_6_5_percent(self):
        """With 5000 Congolese staff, the max expats allowed is 347."""

        # Add 100 expats (Well under the limit)
        for i in range(100):
            self._create_expat(i)

        service = QuotaService(self.company)
        report = service.compute()

        # 100 / 5100 = 1.96%
        self.assertTrue(report.is_compliant)
        self.assertLess(report.sector_pct, 6.5)
        self.assertEqual(report.headroom, 247)  # 347 max - 100 current

    def test_quota_breach_over_6_5_percent(self):
        """If we add 350 expats, it should trigger a breach."""

        # Add 350 expats (Above the 347 limit)
        for i in range(350):
            self._create_expat(i)

        service = QuotaService(self.company)
        report = service.compute()

        # 350 / 5350 = 6.54%
        self.assertFalse(report.is_compliant)
        self.assertGreater(report.sector_pct, 6.5)
        self.assertEqual(report.headroom, 0)
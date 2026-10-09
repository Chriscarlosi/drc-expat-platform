"""Prove tenant isolation works. This is a security test."""

from django.test import TestCase

from apps.organization.models import Company
from apps.organization.context import (
    set_current_tenant, reset_tenant, set_bypass, reset_bypass,
)
from apps.experts.models import ExpertProfile


class TenantIsolationTest(TestCase):
    def setUp(self):
        self.kibali = Company.objects.create(name="Kibali Gold Mine", slug="kibali")
        self.tenke = Company.objects.create(name="Tenke Fungurume", slug="tenke")

        self.expert_kibali = ExpertProfile.objects.create(
            company=self.kibali,
            first_name="Jean", last_name="Dupont",
            date_of_birth="1985-01-01", gender="M",
            nationality="French", is_expatriate=True,
            passport_number="KIB-001",
            passport_issue_date="2020-01-01",
            passport_expiry_date="2027-01-05",
            email="jean@kibali.local",
            employer_company="Kibali Gold Mine",
            job_title="Mining Engineer",
        )
        self.expert_tenke = ExpertProfile.objects.create(
            company=self.tenke,
            first_name="Alice", last_name="Martin",
            date_of_birth="1990-01-01", gender="F",
            nationality="Belgian", is_expatriate=True,
            passport_number="TF-001",
            passport_issue_date="2020-01-01",
            passport_expiry_date="2027-01-05",
            email="alice@tenke.local",
            employer_company="Tenke Fungurume",
            job_title="Geologist",
        )

    def test_no_tenant_returns_empty(self):
        """Without a tenant set, manager returns nothing (fails safe)."""
        self.assertEqual(ExpertProfile.objects.count(), 0)

    def test_tenant_sees_only_its_own_experts(self):
        token = set_current_tenant(self.kibali)
        try:
            self.assertEqual(ExpertProfile.objects.count(), 1)
            self.assertEqual(ExpertProfile.objects.first().first_name, "Jean")
        finally:
            reset_tenant(token)

    def test_tenant_cannot_see_other_tenant_experts(self):
        token = set_current_tenant(self.tenke)
        try:
            names = list(ExpertProfile.objects.values_list("first_name", flat=True))
            self.assertNotIn("Jean", names)
            self.assertIn("Alice", names)
        finally:
            reset_tenant(token)

    def test_bypass_sees_all(self):
        token = set_bypass(True)
        try:
            self.assertEqual(ExpertProfile.objects.count(), 2)
        finally:
            reset_bypass(token)

    def test_explicit_unscoped_returns_all(self):
        token = set_current_tenant(self.kibali)
        try:
            self.assertEqual(ExpertProfile.objects.count(), 1)
            self.assertEqual(ExpertProfile.objects.unscoped().count(), 2)
        finally:
            reset_tenant(token)
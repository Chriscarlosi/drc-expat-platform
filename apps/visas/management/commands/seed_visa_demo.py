"""
Seed demo data for testing dashboard alerts and prolongation workflows.
Creates a dummy Expert and Company if none exist.
Run: python manage.py seed_visa_demo
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta

from apps.visas.models import CarteDeTravail, VisaRecord, VisaProlongation, VisaTypeCatalog
from apps.experts.models import ExpertProfile
from apps.organization.models import Company


class Command(BaseCommand):
    help = "Seed demo visa records with various statuses."

    def handle(self, *args, **options):
        # 1. Ensure we have an Expert to attach the visas to
        company, _ = Company.objects.get_or_create(name="Demo Mining Corp")

        expert, created = ExpertProfile.objects.get_or_create(
            passport_number="DEMO-P123456",
            defaults={
                "first_name": "Demo",
                "last_name": "Expert",
                "date_of_birth": date(1980, 1, 1),
                "gender": "M",
                "nationality": "South African",
                "passport_issue_date": date(2020, 1, 1),
                "passport_expiry_date": date(2030, 1, 1),
                "employer_company": "Demo Mining Corp",
                "job_title": "Senior Geologist",
                "email": "demo.expert@example.com",
                "company": company,
                "is_expatriate": True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created demo expert: {expert.full_name}"))

        # 2. Fetch Visa Types
        vet_type = VisaTypeCatalog.objects.filter(code='VET').first()
        veo_type = VisaTypeCatalog.objects.filter(code='VEO').first()
        prolong_type = VisaTypeCatalog.objects.filter(code='VV2+').first()

        if not vet_type or not veo_type:
            self.stdout.write(self.style.ERROR("Catalog missing VET or VEO. Run seed_visa_catalog first."))
            return

        today = timezone.now().date()

        # 3. Create Expired Visa (VEO - 12 months validity)
        expired_issue = today - relativedelta(months=13)
        expired_expiry = expired_issue + relativedelta(months=veo_type.validity_months)

        VisaRecord.objects.get_or_create(
            visa_number="VISA-DEMO-EXP-01",
            defaults={
                'expert': expert, 'visa_type': veo_type,
                'issue_date': expired_issue,
                'expiry_date': expired_expiry,
                'status': VisaRecord.Status.EXPIRED
            }
        )

        # 4. Create Expiring Soon Visa (VET - 24 months validity, expiring in 45 days)
        soon_expiry = today + timedelta(days=45)
        soon_issue = soon_expiry - relativedelta(months=vet_type.validity_months)

        VisaRecord.objects.get_or_create(
            visa_number="VISA-DEMO-SOON-01",
            defaults={
                'expert': expert, 'visa_type': vet_type,
                'issue_date': soon_issue,
                'expiry_date': soon_expiry,
                'status': VisaRecord.Status.EXPIRING_SOON
            }
        )

        # 5. Create Active Visa for Prolongation Test (VET - 24 months validity)
        active_issue = today
        active_expiry = active_issue + relativedelta(months=vet_type.validity_months)

        # 5.1 Ticket 2 Requirement: Create a valid Carte de Travail for the Active VET Visa
        CarteDeTravail.objects.get_or_create(
            permit_number="PERMIT-DEMO-01",
            defaults={
                'expert': expert,
                'issue_date': today,
                'expiry_date': active_expiry + relativedelta(days=30),  # Must extend beyond visa
                'issuing_authority': "Ministère du Travail",
                'is_active': True
            }
        )

        active_visa, _ = VisaRecord.objects.get_or_create(
            visa_number="VISA-DEMO-ACT-01",
            defaults={
                'expert': expert, 'visa_type': vet_type,
                'issue_date': active_issue,
                'expiry_date': active_expiry,
                'status': VisaRecord.Status.ACTIVE
            }
        )

        # 6. Create Prolongation Record (Approved)
        if prolong_type:
            VisaProlongation.objects.get_or_create(
                prolongation_number="PROL-DEMO-0001",
                defaults={
                    'expert': expert, 'parent_visa': active_visa,
                    'prolongation_type': prolong_type,
                    'request_date': today - timedelta(days=30),
                    'new_expiry_date': active_visa.expiry_date + relativedelta(months=2),
                    'status': VisaProlongation.Status.APPROVED,
                    'approval_date': today - timedelta(days=25),
                }
            )

            # 7. Create Prolongation Record (Rejected)
            VisaProlongation.objects.get_or_create(
                prolongation_number="PROL-DEMO-0002",
                defaults={
                    'expert': expert, 'parent_visa': active_visa,
                    'prolongation_type': prolong_type,
                    'request_date': today - timedelta(days=10),
                    'new_expiry_date': active_visa.expiry_date + relativedelta(months=2),
                    'status': VisaProlongation.Status.REJECTED,
                    'approval_date': today - timedelta(days=5),
                }
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded demo visa records!"))
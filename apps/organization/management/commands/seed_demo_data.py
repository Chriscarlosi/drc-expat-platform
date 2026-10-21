"""
Seed realistic DRC expat data for Kibali Gold Mine.

Run: python manage.py seed_demo_data

Creates:
  • 3 sites, 5 departments
  • 20 experts across 5 nationalities
  • Cartes de travail (some healthy, some expiring, some expired)
  • Visas (mix of types)
  • Penalties (2 irregular experts)
  • Costs (visa fees, medical, legal for a few)
  • Login accounts for a few key users
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from apps.organization.models import Company, Site, Department, UserCompanyMembership
from apps.experts.models import ExpertProfile
from apps.visas.models import CarteDeTravail, VisaRecord, VisaTypeCatalog
from apps.compliance.models import PenaltyLedger, CostCategory, ExpertCost


# ─── Realistic data pools ────────────────────────────────────
NATIONALITIES = [
    ("French", "FR"), ("Belgian", "BE"), ("South African", "ZA"),
    ("Indian", "IN"), ("Chinese", "CN"), ("Australian", "AU"),
]

MALE_NAMES = [
    ("Jean", "Dupont"), ("Marc", "Lefevre"), ("Peter", "Van Der Merwe"),
    ("Rajesh", "Kumar"), ("Wei", "Chen"), ("Michael", "O'Brien"),
    ("Patrick", "Nkulu"), ("Ahmed", "Hassan"),
]
FEMALE_NAMES = [
    ("Marie", "Dubois"), ("Sophie", "Laurent"), ("Anna", "Pretorius"),
    ("Priya", "Sharma"), ("Mei", "Wang"), ("Sarah", "Botha"),
]

JOB_TITLES = [
    ("Senior Mining Engineer", "Ingénieur Minier Senior"),
    ("Chief Geologist", "Géologue en Chef"),
    ("Processing Plant Manager", "Directeur Usine de Traitement"),
    ("HSEC Manager", "Responsable HSE"),
    ("Underground Operations Lead", "Chef Opérations Souterraines"),
    ("Metallurgist", "Métallurgiste"),
    ("Finance Controller", "Contrôleur Financier"),
    ("IT Infrastructure Lead", "Responsable Infrastructure IT"),
    ("HR Business Partner", "Partenaire RH"),
    ("Logistics Coordinator", "Coordinateur Logistique"),
    ("Maintenance Superintendent", "Superintendant Maintenance"),
    ("Exploration Manager", "Directeur Exploration"),
]


class Command(BaseCommand):
    help = "Seed realistic Kibali Gold Mine demo data for the platform."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=20,
            help="Number of experts to create (default: 20).",
        )
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete existing demo data first (experts only, keeps users).",
        )

    def handle(self, *args, **options):
        count = options["count"]
        reset = options["reset"]

        random.seed(42)  # deterministic

        # ─── 1. Company ─────────────────────────────────────
        company, _ = Company.objects.update_or_create(
            slug="kibali",
            defaults={
                "name": "Kibali Gold Mine",
                "dgm_registration": "KGM-DGM-2025-001",
                "tax_id": "A1234567B",
                "congolese_staff_count": 5000,
                "contact_email": "compliance@kibali.local",
                "contact_phone": "+243 123 456 789",
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"✅ Company: {company.name}"))

        # ─── 2. Sites ───────────────────────────────────────
        sites_data = [
            ("Kibali Underground", "KGM-UG", "Haut-Uélé"),
            ("Kibali Processing Plant", "KGM-PP", "Haut-Uélé"),
            ("Kibali Open Pit", "KGM-OP", "Haut-Uélé"),
        ]
        sites = []
        for name, code, province in sites_data:
            s, _ = Site.objects.update_or_create(
                company=company, code=code,
                defaults={"name": name, "province": province},
            )
            sites.append(s)
        self.stdout.write(self.style.SUCCESS(f"✅ Sites: {len(sites)}"))

        # ─── 3. Departments ─────────────────────────────────
        depts_data = [
            ("Mining Operations", "MINING"),
            ("Processing", "PROC"),
            ("HR & Administration", "HR"),
            ("Finance", "FIN"),
            ("IT & Digital", "IT"),
        ]
        depts = []
        for name, code in depts_data:
            d, _ = Department.objects.update_or_create(
                company=company, code=code,
                defaults={"name": name},
            )
            depts.append(d)
        self.stdout.write(self.style.SUCCESS(f"✅ Departments: {len(depts)}"))

        # ─── 4. Reset experts (optional) ────────────────────
        if reset:
            deleted = ExpertProfile.objects.unscoped().filter(
                company=company
            ).delete()
            self.stdout.write(self.style.WARNING(f"🗑  Cleared {deleted[0]} existing experts."))

        # ─── 5. Visa catalog (ensure exists) ────────────────
        visa_types = list(VisaTypeCatalog.objects.all())
        if not visa_types:
            self.stdout.write(self.style.ERROR(
                "❌ No VisaTypeCatalog entries. Run: python manage.py seed_visa_catalog"
            ))
            return

        # ─── 6. Create experts ──────────────────────────────
        today = date.today()
        created_count = 0

        for i in range(count):
            # Names
            if random.random() < 0.75:
                first, last = random.choice(MALE_NAMES)
                gender = "M"
            else:
                first, last = random.choice(FEMALE_NAMES)
                gender = "F"

            # Unique demo identifier — use ONEM (plaintext field) for dedup check.
            # passport_number is EncryptedCharField (ciphertext randomized per call),
            # so filtering on it silently fails and creates duplicates.
            onem_number = f"ONEM-DEMO-{1000 + i}"

            if ExpertProfile.objects.unscoped().filter(
                    onem_registry_number=onem_number
            ).exists():
                continue

            passport_number = f"DEMO{1000 + i}"
            passport_number = f"DEMO{1000 + i}"

            nationality, _ = random.choice(NATIONALITIES)
            job_en, job_fr = random.choice(JOB_TITLES)
            site = random.choice(sites)
            dept = random.choice(depts)

            # Passport expiry: 80% healthy (>180d), 15% expiring (30-90d), 5% expired
            rand = random.random()
            if rand < 0.80:
                passport_expiry = today + timedelta(days=random.randint(180, 900))
            elif rand < 0.95:
                passport_expiry = today + timedelta(days=random.randint(30, 90))
            else:
                passport_expiry = today - timedelta(days=random.randint(10, 60))

            # Yellow fever: 90% valid, 10% expired
            yf_expiry = (
                today + timedelta(days=random.randint(60, 900))
                if random.random() < 0.9
                else today - timedelta(days=random.randint(10, 90))
            )

            expert = ExpertProfile.objects.unscoped().create(
                company=company,
                site=site,
                department=dept,
                first_name=first,
                last_name=last,
                date_of_birth=date(
                    random.randint(1965, 1995),
                    random.randint(1, 12),
                    random.randint(1, 28),
                ),
                gender=gender,
                nationality=nationality,
                is_expatriate=True,
                passport_number=passport_number,
                passport_issue_date=today - timedelta(days=random.randint(400, 2000)),
                passport_expiry_date=passport_expiry,
                yellow_fever_card_number=f"YF-{1000 + i}",
                yellow_fever_expiry_date=yf_expiry,
                onem_registry_number=f"ONEM-{1000 + i}",
                employer_company="Kibali Gold Mine",
                job_title=job_en,
                job_title_fr=job_fr,
                email=f"{first.lower()}.{last.lower().replace(' ', '').replace(chr(39), '')}@kibali.local",
                phone=f"+243{random.randint(800000000, 899999999)}",
                job_category=random.choice([
                    ExpertProfile.JobCategory.CLASS_I_V,
                    ExpertProfile.JobCategory.SUPERVISOR,
                    ExpertProfile.JobCategory.MANAGEMENT,
                ]),
                is_active=True,
                notes=f"Demo expert #{i + 1}",
            )
            created_count += 1

            # ─── Carte de travail (80% of experts) ──────────
            if random.random() < 0.8:
                carte_rand = random.random()
                if carte_rand < 0.7:
                    carte_expiry = today + timedelta(days=random.randint(120, 700))
                elif carte_rand < 0.9:
                    carte_expiry = today + timedelta(days=random.randint(20, 90))
                else:
                    carte_expiry = today - timedelta(days=random.randint(5, 40))

                CarteDeTravail.objects.create(
                    expert=expert,
                    permit_number=f"CT-{2000 + i}",
                    issue_date=today - timedelta(days=random.randint(60, 300)),
                    expiry_date=carte_expiry,
                    issuing_authority="Ministère du Travail",
                    is_active=True,
                )

            # ─── Visa record (70% of experts) ───────────────
            if random.random() < 0.7 and visa_types:
                vt = random.choice(visa_types)
                visa_expiry = today + timedelta(days=random.randint(30, 600))
                VisaRecord.objects.create(
                    expert=expert,
                    visa_type=vt,
                    visa_number=f"VISA-{3000 + i}",
                    issue_date=today - timedelta(days=random.randint(15, 200)),
                    expiry_date=visa_expiry,
                    status=random.choice(["ACTIVE", "ACTIVE", "ACTIVE", "PENDING"]),
                    dgm_reference=f"DGM-REF-{i:04d}",
                    notes=f"Demo visa for {expert.full_name}",
                )

        self.stdout.write(self.style.SUCCESS(f"✅ Created {created_count} experts"))

        # ─── 7. Penalties (2-3 irregular experts) ───────────
        irregular = list(
            ExpertProfile.objects.unscoped().filter(company=company)[:3]
        )
        penalty_created = 0
        for e in irregular:
            if random.random() < 0.3:  # ~30% chance
                PenaltyLedger.objects.create(
                    expert=e,
                    reason=random.choice([
                        PenaltyLedger.Reason.OVERSTAY,
                        PenaltyLedger.Reason.EXPIRED_VISA,
                        PenaltyLedger.Reason.NO_PERMIT,
                    ]),
                    accrual_start_date=today - timedelta(days=random.randint(5, 45)),
                    daily_rate_usd=Decimal("150.00"),
                    resolved=False,
                    resolution_notes="Under review by compliance team",
                )
                penalty_created += 1
        self.stdout.write(self.style.SUCCESS(f"✅ Created {penalty_created} penalties"))

        # ─── 8. Costs (random sample) ───────────────────────
        categories = list(CostCategory.objects.filter(is_active=True))
        cost_created = 0
        if categories:
            sample_experts = list(
                ExpertProfile.objects.unscoped().filter(company=company)[:10]
            )
            for e in sample_experts:
                for _ in range(random.randint(1, 3)):
                    cat = random.choice(categories)
                    ExpertCost.objects.create(
                        expert=e,
                        category=cat,
                        description=f"{cat.name_en} for {e.full_name}",
                        amount=Decimal(str(random.randint(80, 2500))),
                        currency=ExpertCost.Currency.USD,
                        incurred_date=today - timedelta(days=random.randint(5, 180)),
                        status=random.choice([
                            ExpertCost.Status.APPROVED,
                            ExpertCost.Status.INVOICED,
                            ExpertCost.Status.PAID,
                        ]),
                    )
                    cost_created += 1
        self.stdout.write(self.style.SUCCESS(f"✅ Created {cost_created} expert costs"))

        # ─── 9. HR Manager user ────────────────────────────
        hr_user, created = User.objects.get_or_create(
            username="hr_manager",
            defaults={
                "email": "hr@kibali.local",
                "first_name": "HR",
                "last_name": "Manager",
                "is_staff": True,
            },
        )
        if created:
            hr_user.set_password("DrcHR2026!")
            hr_user.save()

        UserCompanyMembership.objects.update_or_create(
            user=hr_user, company=company,
            defaults={
                "role": UserCompanyMembership.Role.HR_MANAGER,
                "is_default": True,
                "is_active": True,
            },
        )

        # ─── 10. Mining Department Manager ──────────────────
        mining_dept = Department.objects.filter(company=company, code="MINING").first()
        if mining_dept:
            dm_user, created = User.objects.get_or_create(
                username="mining_mgr",
                defaults={
                    "email": "mining.mgr@kibali.local",
                    "first_name": "Mining",
                    "last_name": "Manager",
                    "is_staff": True,
                },
            )
            if created:
                dm_user.set_password("DrcMINING2026!")
                dm_user.save()

            UserCompanyMembership.objects.update_or_create(
                user=dm_user, company=company,
                defaults={
                    "role": UserCompanyMembership.Role.DEPARTMENT_MANAGER,
                    "department": mining_dept,
                    "is_default": True,
                    "is_active": True,
                },
            )

        # ─── Summary ────────────────────────────────────────
        self.stdout.write("\n" + "═" * 60)
        self.stdout.write(self.style.SUCCESS("✅ SEED COMPLETE"))
        self.stdout.write("═" * 60)
        self.stdout.write(f"   Company         : {company.name}")
        self.stdout.write(f"   Total experts   : {ExpertProfile.objects.unscoped().filter(company=company).count()}")
        self.stdout.write(f"   Total penalties : {PenaltyLedger.objects.count()}")
        self.stdout.write(f"   Total costs     : {ExpertCost.objects.count()}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("   🔐 Demo credentials:"))
        self.stdout.write("      HR Manager     : hr_manager / DrcHR2026!")
        self.stdout.write("      Mining Dept Mgr: mining_mgr / DrcMINING2026!")
        self.stdout.write("═" * 60 + "\n")
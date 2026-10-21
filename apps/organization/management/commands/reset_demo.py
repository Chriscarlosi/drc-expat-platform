"""
Reset the platform to a curated Kibali demo state.

Usage:
    python manage.py reset_demo           # asks for confirmation
    python manage.py reset_demo --yes     # skip confirmation

Wipes:
    • All experts, cartes, visas, penalties, costs, invoices
    • All flights, passengers, rotations, dependants, authorizations
    • All document versions

Keeps:
    • Users (superuser, hr_manager, mining_mgr)
    • Companies, Sites, Departments
    • Charter operators, aircraft, routes
    • Visa type catalog, cost categories, alert tiers
    • Audit log (compromised — cannot be deleted by design)

Rebuilds:
    • 12 curated experts across 4 compliance scenarios
    • 14-day flight schedule on real DKB routes
    • Rotations, costs, dependants, travel authorizations
"""

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "Reset the platform to a curated Kibali demo state."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Skip confirmation.")

    def handle(self, *args, **options):
        if not options["yes"]:
            confirm = input(
                "\n⚠️  This will DELETE all experts, flights, costs, and documents.\n"
                "   Audit log and users will be preserved.\n"
                "   Type 'yes' to continue: "
            )
            if confirm != "yes":
                self.stdout.write(self.style.WARNING("Cancelled."))
                return

        random.seed(2026)
        with transaction.atomic():
            self._wipe()
            self._rebuild()

        self.stdout.write(self.style.SUCCESS("\n🎉 Demo reset complete.\n"))

    # ═══════════════════════════════════════════════════════════════
    # WIPE
    # ═══════════════════════════════════════════════════════════════

    def _wipe(self):
        self.stdout.write("\n🗑  Wiping business data...\n")

        # Order matters — respect FK dependencies
        tables = [
            # Auths reference flights + experts
            "travel_travelauthorization_accompanying_dependants",
            "travel_travelauthorization",
            # Passengers reference flights + experts
            "travel_charterpassenger",
            # Now flights
            "travel_charterflight",
            # Dependants + rotations
            "travel_dependant",
            "travel_rotationschedule",
            # Notifications (has FK to experts)
            "notifications_alertlog",
            # Standalone
            "documents_documentversion",
            "compliance_expertcost",
            "compliance_monthlyinvoice",
            "compliance_penaltyledger",
            # Visas — prolongations → records → subclasses → cartes
            "visas_visaprolongation",
            "visas_visarecord",
            "visas_establishmentvisa",
            "visas_voyagevisa",
            "visas_airportvisa",
            "visas_flyingvisa",
            "visas_cartedetravail",
            # Parent last
            "experts_expertprofile",
        ]

        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM {table};")
                    self.stdout.write(f"  ✓ Cleared {table}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  ⚠ Skip {table}: {e}"))
    # ═══════════════════════════════════════════════════════════════
    # REBUILD
    # ═══════════════════════════════════════════════════════════════

    def _rebuild(self):
        from apps.experts.models import ExpertProfile
        from apps.visas.models import (
            CarteDeTravail, VisaRecord, VisaTypeCatalog,
        )
        from apps.compliance.models import (
            PenaltyLedger, CostCategory, ExpertCost,
        )
        from apps.organization.models import Company, Site, Department
        from apps.travel.models import (
            CharterOperator, Aircraft, CharterRoute, CharterFlight,
            CharterPassenger, Dependant, RotationSchedule, TravelAuthorization,
        )

        self.stdout.write("\n🏗  Rebuilding curated demo data...\n")

        # ── Company + sites + departments ──────────────────────
        company = Company.objects.get(slug="kibali")
        company.congolese_staff_count = 5000
        company.save()

        sites = {s.code: s for s in Site.objects.filter(company=company)}
        depts = {d.code: d for d in Department.objects.filter(company=company)}

        site_ug = sites.get("KGM-UG") or sites.get("UG")
        site_pp = sites.get("KGM-PP") or sites.get("PP")
        site_op = sites.get("KGM-OP") or sites.get("OP")

        dept_mining = depts.get("MINING")
        dept_proc = depts.get("PROC")
        dept_hr = depts.get("HR")
        dept_fin = depts.get("FIN")
        dept_it = depts.get("IT")

        today = date.today()

        # ═══════════════════════════════════════════════════════
        # EXPERTS — 12 curated, story-driven
        # ═══════════════════════════════════════════════════════
        experts_data = [
            # (first, last, gender, nationality, job_en, job_fr, site, dept,
            #  passport_expiry_days, yf_expiry_days, carte_days,
            #  has_visa, job_category)
            ("Jean-Marc", "Delacroix", "M", "French",
             "Senior Mining Engineer", "Ingénieur Minier Senior",
             site_ug, dept_mining, 540, 400, 480, True, "MANAGEMENT"),

            ("Sophie", "Bernard", "F", "French",
             "HSEC Manager", "Responsable HSE",
             site_ug, dept_hr, 45, 300, 380, True, "SUPERVISOR"),

            ("Rajesh", "Patel", "M", "Indian",
             "Processing Plant Manager", "Directeur Usine de Traitement",
             site_pp, dept_proc, 85, 500, 600, True, "MANAGEMENT"),

            ("Ahmed", "Hassan", "M", "South African",
             "Underground Supervisor", "Superviseur Souterrain",
             site_ug, dept_mining, 25, 250, 320, True, "SUPERVISOR"),

            ("Wei", "Chen", "M", "Chinese",
             "IT Infrastructure Lead", "Responsable Infrastructure IT",
             site_pp, dept_it, 420, 350, -40, True, "CLASS_I_V"),  # CARTE EXPIRED 40d

            ("Marcus", "Thompson", "M", "Australian",
             "Metallurgist", "Métallurgiste",
             site_pp, dept_proc, 380, 600, 45, True, "CLASS_I_V"),

            ("Sarah", "O'Sullivan", "F", "Australian",
             "Finance Controller", "Contrôleur Financier",
             site_op, dept_fin, 620, 700, 550, True, "MANAGEMENT"),

            ("Pierre", "Moreau", "M", "Belgian",
             "Exploration Manager", "Directeur Exploration",
             site_op, dept_mining, 200, 400, 720, True, "MANAGEMENT"),

            ("David", "Van Wyk", "M", "South African",
             "Maintenance Superintendent", "Superintendant Maintenance",
             site_pp, dept_proc, 310, 500, 260, True, "SUPERVISOR"),

            ("Li", "Wei", "M", "Chinese",
             "Logistics Coordinator", "Coordinateur Logistique",
             site_ug, dept_mining, 150, 350, 200, True, "CLASS_I_V"),

            ("Arun", "Kumar", "M", "Indian",
             "Chief Geologist", "Géologue en Chef",
             site_op, dept_mining, 700, 800, 900, True, "MANAGEMENT"),

            ("Marie", "Dubois", "F", "French",
             "HR Business Partner", "Partenaire RH",
             site_ug, dept_hr, 90, 200, 55, False, "CLASS_I_V"),  # No visa yet
        ]

        experts = []
        for i, (fn, ln, gender, nationality, job_en, job_fr,
                site, dept, p_exp, yf_exp, carte_days,
                has_visa, job_cat) in enumerate(experts_data, 1):

            passport_expiry = today + timedelta(days=p_exp)
            yf_expiry = today + timedelta(days=yf_exp)

            e = ExpertProfile.objects.unscoped().create(
                company=company,
                site=site,
                department=dept,
                first_name=fn,
                last_name=ln,
                date_of_birth=date(random.randint(1965, 1990), random.randint(1, 12), random.randint(1, 28)),
                gender=gender,
                nationality=nationality,
                is_expatriate=True,
                passport_number=f"DEMO{2000 + i}",
                passport_issue_date=today - timedelta(days=random.randint(500, 1500)),
                passport_expiry_date=passport_expiry,
                yellow_fever_card_number=f"YF-DEMO-{2000 + i}",
                yellow_fever_expiry_date=yf_expiry,
                onem_registry_number=f"ONEM-DEMO-{2000 + i}",
                employer_company="Kibali Gold Mine",
                job_title=job_en,
                job_title_fr=job_fr,
                job_category=job_cat,
                email=f"{fn.lower().replace('-', '.').replace(' ', '')}.{ln.lower().replace(' ', '').replace(chr(39), '')}@kibali.local",
                phone=f"+243{random.randint(800000000, 899999999)}",
                is_active=True,
                notes=f"Demo expert #{i}",
            )
            experts.append(e)

            # ── Carte de travail ────────────────────────────
            if carte_days is not None:
                carte_issue = today - timedelta(days=300)
                carte_expiry = today + timedelta(days=carte_days)
                CarteDeTravail.objects.create(
                    expert=e,
                    permit_number=f"CT-DEMO-{2000 + i}",
                    issue_date=carte_issue,
                    expiry_date=carte_expiry,
                    issuing_authority="Ministère du Travail",
                    is_active=True,
                )

            # ── Visa record ─────────────────────────────────
            if has_visa:
                try:
                    vt = VisaTypeCatalog.objects.get(code="VET")
                    VisaRecord.objects.create(
                        expert=e,
                        visa_type=vt,
                        visa_number=f"VISA-DEMO-{3000 + i}",
                        issue_date=today - timedelta(days=180),
                        expiry_date=today + timedelta(days=random.randint(200, 600)),
                        status="ACTIVE",
                        dgm_reference=f"DGM-REF-{i:04d}",
                    )
                except VisaTypeCatalog.DoesNotExist:
                    pass

        self.stdout.write(self.style.SUCCESS(f"  ✅ {len(experts)} experts created"))

        # ═══════════════════════════════════════════════════════
        # PENALTIES — the "irregular" story
        # ═══════════════════════════════════════════════════════
        wei = experts[4]  # Wei Chen
        ahmed = experts[3]  # Ahmed Hassan

        PenaltyLedger.objects.create(
            expert=wei,
            reason=PenaltyLedger.Reason.EXPIRED_VISA,
            accrual_start_date=today - timedelta(days=40),
            daily_rate_usd=Decimal("150.00"),
            resolved=False,
            resolution_notes="Carte de Travail expired 40 days ago. Under investigation.",
        )
        PenaltyLedger.objects.create(
            expert=ahmed,
            reason=PenaltyLedger.Reason.OVERSTAY,
            accrual_start_date=today - timedelta(days=14),
            daily_rate_usd=Decimal("100.00"),
            resolved=False,
            resolution_notes="Passport expiring — renewal in progress.",
        )
        self.stdout.write(self.style.SUCCESS(f"  ✅ 2 penalties created"))

        # ═══════════════════════════════════════════════════════
        # COSTS
        # ═══════════════════════════════════════════════════════
        cat_map = {c.code: c for c in CostCategory.objects.all()}
        cost_codes = ["VISA_FEE", "CARTE_FEE", "MEDICAL", "YELLOW_FEVER", "TRANSLATION", "TRAVEL"]
        cost_total = 0
        for e in experts:
            for _ in range(random.randint(2, 4)):
                code = random.choice(cost_codes)
                cat = cat_map.get(code)
                if not cat:
                    continue
                amount = Decimal(str(random.randint(80, 1200)))
                ExpertCost.objects.create(
                    expert=e,
                    category=cat,
                    description=f"{cat.name_en} for {e.full_name}",
                    amount=amount,
                    currency=ExpertCost.Currency.USD,
                    incurred_date=today - timedelta(days=random.randint(5, 180)),
                    status=ExpertCost.Status.PAID if random.random() < 0.7 else ExpertCost.Status.INVOICED,
                )
                cost_total += 1
        self.stdout.write(self.style.SUCCESS(f"  ✅ {cost_total} cost entries created"))

        # ═══════════════════════════════════════════════════════
        # DEPENDANTS — Sarah's family
        # ═══════════════════════════════════════════════════════
        sarah = experts[6]  # Sarah O'Sullivan
        Dependant.objects.create(
            expert=sarah, first_name="Liam", last_name="O'Sullivan",
            date_of_birth=date(2018, 3, 15), relationship="CHILD",
            nationality="Australian", passport_number="DEMO-AU-001",
            passport_expiry_date=today + timedelta(days=600),
            is_travel_eligible=True,
        )
        Dependant.objects.create(
            expert=sarah, first_name="Aoife", last_name="O'Sullivan",
            date_of_birth=date(2020, 7, 22), relationship="CHILD",
            nationality="Australian", passport_number="DEMO-AU-002",
            passport_expiry_date=today + timedelta(days=600),
            is_travel_eligible=True,
        )
        self.stdout.write(self.style.SUCCESS(f"  ✅ 2 dependants created"))

        # ═══════════════════════════════════════════════════════
        # ROTATIONS — all 12 experts
        # ═══════════════════════════════════════════════════════
        patterns = ["4_4", "6_3", "8_4", "28_28"]
        for e in experts:
            RotationSchedule.objects.create(
                expert=e,
                pattern=random.choice(patterns),
                cycle_start_date=today - timedelta(days=random.randint(5, 45)),
                is_active=True,
            )
        self.stdout.write(self.style.SUCCESS(f"  ✅ 12 rotations created"))

        # ═══════════════════════════════════════════════════════
        # FLIGHTS — 14-day schedule on DOK routes
        # ═══════════════════════════════════════════════════════
        try:
            kibali_op = CharterOperator.objects.get(code="KIBALI")
            maf_op = CharterOperator.objects.get(code="MAF")
            bar_op = CharterOperator.objects.get(code="BAR-AVIATION")
            zs_bgo = Aircraft.objects.get(registration="ZS-BGO")
            zs_bgm = Aircraft.objects.get(registration="ZS-BGM")
            zs_kgm = Aircraft.objects.get(registration="ZS-KGM")
            maf_1 = Aircraft.objects.get(registration="ZS-MAF1")
            bar_1 = Aircraft.objects.get(registration="ZS-BAR1")
        except (CharterOperator.DoesNotExist, Aircraft.DoesNotExist) as exc:
            self.stdout.write(self.style.WARNING(f"  ⚠ Skipping flights — {exc}"))
            return

        routes = {f"{r.origin_iata}-{r.destination_iata}": r for r in CharterRoute.objects.all()}

        flight_plan = [
            # (days from today, hour, route_key, operator, aircraft, pax_experts, dgm, medevac)
            (1, 7, "DOK-EBB", kibali_op, zs_bgo, [0, 1], False, False),
            (1, 15, "EBB-DOK", kibali_op, zs_bgo, [4, 6], True, False),
            (2, 8, "DOK-MWZ", kibali_op, zs_kgm, [2, 3], False, False),
            (3, 9, "DOK-JNB", bar_op, bar_1, [6], False, False),
            (4, 8, "DOK-NBO", kibali_op, zs_bgm, [7, 8], False, True),
            (5, 7, "DOK-EBB", maf_op, maf_1, [9], False, False),
            (6, 10, "DOK-GRB", kibali_op, zs_kgm, [10], False, False),
            (7, 8, "DOK-BUX", kibali_op, zs_bgo, [11], False, False),
            (8, 7, "DOK-EBB", kibali_op, zs_bgm, [0, 2], False, False),
            (10, 9, "EBB-DOK", kibali_op, zs_bgo, [3, 5], True, False),
            (11, 8, "DOK-MWZ", kibali_op, zs_kgm, [1], False, False),
            (13, 7, "DOK-EBB", maf_op, maf_1, [6, 7], False, False),
            (14, 8, "DOK-NBO", kibali_op, zs_bgm, [8, 9, 10], False, True),
        ]

        flights_created = 0
        for i, (days, hour, route_key, operator, aircraft, expert_idxs, dgm, medevac) in enumerate(flight_plan, 1):
            route = routes.get(route_key)
            if not route:
                continue

            dep = timezone.make_aware(
                datetime.combine(today + timedelta(days=days), time(hour, 0))
            )
            arr = dep + timedelta(minutes=route.typical_duration_minutes or 120)

            flight = CharterFlight.objects.create(
                flight_number=f"KGM-{1000 + i}",
                operator=operator,
                aircraft=aircraft,
                route=route,
                departure_datetime=dep,
                arrival_datetime=arr,
                status=CharterFlight.Status.SCHEDULED,
                seats_available=aircraft.capacity_passengers,
                dgm_manifest_submitted=dgm,
                dgm_manifest_submitted_at=timezone.now() if dgm else None,
                medevac_ready=medevac,
            )
            flights_created += 1

            # Add passengers
            seat_num = 1
            for idx in expert_idxs:
                if idx >= len(experts):
                    continue
                e = experts[idx]
                CharterPassenger.objects.create(
                    flight=flight,
                    passenger_type=CharterPassenger.PassengerType.EXPERT,
                    expert=e,
                    seat_number=f"{seat_num}A",
                    status=CharterPassenger.BookingStatus.CONFIRMED,
                    ticket_cost_usd=Decimal(str(random.randint(350, 850))),
                )
                seat_num += 1

        self.stdout.write(self.style.SUCCESS(f"  ✅ {flights_created} flights + passengers created"))

        # ═══════════════════════════════════════════════════════
        # TRAVEL AUTHORIZATIONS — 4 states
        # ═══════════════════════════════════════════════════════
        routes_dok_ebb = routes.get("DOK-EBB")

        TravelAuthorization.objects.create(
            request_number="TA-2026-001",
            expert=experts[1],  # Sophie
            purpose=TravelAuthorization.Purpose.ROTATION,
            route=routes_dok_ebb,
            requested_departure_date=today + timedelta(days=20),
            requested_return_date=today + timedelta(days=48),
            status=TravelAuthorization.Status.DRAFT,
            justification="Standard 4/4 rotation.",
        )

        TravelAuthorization.objects.create(
            request_number="TA-2026-002",
            expert=experts[2],  # Rajesh
            purpose=TravelAuthorization.Purpose.BUSINESS,
            route=routes_dok_ebb,
            requested_departure_date=today + timedelta(days=10),
            requested_return_date=today + timedelta(days=17),
            status=TravelAuthorization.Status.PENDING_MANAGER,
            justification="Kinshasa processing plant review.",
        )

        TravelAuthorization.objects.create(
            request_number="TA-2026-003",
            expert=experts[6],  # Sarah (family)
            purpose=TravelAuthorization.Purpose.FAMILY_VISIT,
            route=routes_dok_ebb,
            requested_departure_date=today + timedelta(days=30),
            requested_return_date=today + timedelta(days=58),
            status=TravelAuthorization.Status.PENDING_HR,
            justification="Family rotation with 2 dependants.",
            manager_approved_by_repr="mining_mgr",
            manager_approved_at=timezone.now(),
        )

        TravelAuthorization.objects.create(
            request_number="TA-2026-004",
            expert=experts[0],  # Jean-Marc
            purpose=TravelAuthorization.Purpose.TRAINING,
            route=routes_dok_ebb,
            requested_departure_date=today + timedelta(days=45),
            requested_return_date=today + timedelta(days=60),
            status=TravelAuthorization.Status.APPROVED,
            justification="Annual safety certification in Johannesburg.",
            manager_approved_by_repr="hr_manager",
            manager_approved_at=timezone.now(),
            hr_approved_by_repr="hr_manager",
            hr_approved_at=timezone.now(),
        )
        self.stdout.write(self.style.SUCCESS(f"  ✅ 4 travel authorizations created"))

        # ═══════════════════════════════════════════════════════
        # SUMMARY
        # ═══════════════════════════════════════════════════════
        self.stdout.write("\n" + "═" * 60)
        self.stdout.write(self.style.SUCCESS("📊 DEMO STATE SUMMARY"))
        self.stdout.write("═" * 60)
        self.stdout.write(f"  Experts            : {ExpertProfile.objects.unscoped().count()}")
        self.stdout.write(f"  Cartes de travail  : {CarteDeTravail.objects.count()}")
        self.stdout.write(f"  Visa records       : {VisaRecord.objects.count()}")
        self.stdout.write(f"  Active penalties   : {PenaltyLedger.objects.filter(resolved=False).count()}")
        self.stdout.write(f"  Cost entries       : {ExpertCost.objects.count()}")
        self.stdout.write(f"  Dependants         : {Dependant.objects.count()}")
        self.stdout.write(f"  Rotations          : {RotationSchedule.objects.count()}")
        self.stdout.write(f"  Charter flights    : {CharterFlight.objects.count()}")
        self.stdout.write(f"  Travel auths       : {TravelAuthorization.objects.count()}")
        self.stdout.write("═" * 60)
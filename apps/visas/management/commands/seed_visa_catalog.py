"""
Populate the VisaTypeCatalog with official DRC visa codes.
Run: python manage.py seed_visa_catalog
"""
from django.core.management.base import BaseCommand
from apps.visas.models import VisaTypeCatalog

VISA_TYPES = [
    # (code, category, name_en, name_fr, min_days, max_days, multiple, needs_carte, sort,
    #  validity_months, allows_prolong, max_prolong, must_exit, source_ref, is_verified, extension_days)

    # --- Verified Rules (Confirmed by User) ---
    ("VET", "ESTABLISHMENT", "Establishment Work Visa", "Visa d'Établissement Travail", 365, 731, True, True, 80, 24,
     True, 2, False, "Gazette / Circular Ref", True, None),
    ("VEO", "ESTABLISHMENT", "Establishment Ordinary Visa", "Visa d'Établissement Ordinaire", 1000, 1150, True, False,
     90, 12, False, 0, False, "Gazette / Circular Ref", True, None),
    ("E-VETS", "ELECTRONIC", "E-Visa Establishment", "E-Visa Établissement", 365, 730, True, False, 120, 1, False, 0,
     True, "E-Visa Rules", True, None),
    ("E-VVL", "ELECTRONIC", "E-Visa Volant", "E-Visa Volant", 1, 90, False, False, 110, 1, True, 1, False,
     "E-Visa Rules", True, None),
    ("VES", "ESTABLISHMENT", "Visa d'Etablissement Special", "Visa d'Établissement Spécial", 1825, 1826, True, True,
     140, 60, True, 1, False, "Special Decree", True, None),

    # --- Prolongation Types (Verified Extension Lengths, Unverified Max Prolongations) ---
    ("VV2+", "PROLONGATION", "Visa Volant 2-month extension", "Visa Volant prolongation 2 mois", 1, 60, False, False,
     20, None, False, 0, False, "Unverified - Pending Gazette", False, 60),
    ("PVV3+", "PROLONGATION", "Priority 3-month extension", "Prolongation prioritaire 3 mois", 1, 90, False, False, 30,
     None, False, 0, False, "Unverified - Pending Gazette", False, 90),
    ("VV6", "PROLONGATION", "Visa Volant 6-month", "Visa Volant 6 mois", 90, 180, True, False, 40, None, False, 0,
     False, "Unverified - Pending Gazette", False, 180),
    ("VSR+", "PROLONGATION", "Regular stay extension", "Prolongation de séjour régulier", 1, 365, True, False, 50, None,
     False, 0, False, "Unverified - Pending Gazette", False, 365),

    # --- Unverified Rules (User explicitly requested these be flagged) ---
    ("VV", "FLYING", "Flying Visa", "Visa Volant", 1, 92, False, False, 10, None, False, 0, False,
     "Unverified - Pending Gazette", False, None),
    ("VA", "AIRPORT", "Airport/Port Visa (7 days)", "Visa Aéroportuaire (7 jours)", 1, 7, False, False, 60, None, False,
     0, True, "Unverified - Pending Gazette", False, None),
    ("VVD", "VOYAGE", "Travel Visa", "Visa de Voyage", 28, 186, True, False, 70, None, False, 0, False,
     "Unverified - Pending Gazette", False, None),
    ("DT", "TRANSIT", "Disposition Transitoire", "Disposition Transitoire", 1, 15, False, False, 100, None, False, 0,
     False, "Unverified - Pending Gazette", False, None),
    ("HOL-EX", "HOLIDAY", "Expat Holiday / Congé Visa", "Visa de Congé Expatrié", 1, 30, False, False, 130, None, False,
     0, False, "Unverified - Pending Gazette", False, None),
]


class Command(BaseCommand):
    help = "Seed the VisaTypeCatalog with official DRC visa codes."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for (code, category, name_en, name_fr, min_d, max_d,
             multiple, needs_carte, sort, val_months,
             allows_prolong, max_prolong, must_exit, source_ref, is_verified, ext_days) in VISA_TYPES:

            obj, created = VisaTypeCatalog.objects.update_or_create(
                code=code,
                defaults={
                    "category": category,
                    "name_en": name_en,
                    "name_fr": name_fr,
                    "min_validity_days": min_d,
                    "max_validity_days": max_d,
                    "allows_multiple_entries": multiple,
                    "requires_carte_de_travail": needs_carte,
                    "sort_order": sort,
                    "is_active": True,
                    "validity_months": val_months,
                    "allows_prolongation": allows_prolong,
                    "max_prolongations": max_prolong,
                    "must_exit_on_expiry": must_exit,
                    "source_reference": source_ref,
                    "is_verified": is_verified,
                    "extension_length_days": ext_days,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created: {code} — {name_en}"))
            else:
                updated_count += 1
                self.stdout.write(f"↻ Updated: {code}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created_count} created, {updated_count} updated. "
            f"Total catalog entries: {VisaTypeCatalog.objects.count()}"
        ))
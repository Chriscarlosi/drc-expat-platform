"""
Populate the VisaTypeCatalog with official DRC visa codes.
Run: python manage.py seed_visa_catalog
"""

from django.core.management.base import BaseCommand
from apps.visas.models import VisaTypeCatalog


VISA_TYPES = [
    # (code, category, name_en, name_fr, min_days, max_days, multiple, needs_carte, sort)
    ("VV", "FLYING", "Flying Visa", "Visa Volant", 1, 92, False, False, 10),
    ("VV2+", "PROLONGATION", "Visa Volant 2-month extension", "Visa Volant prolongation 2 mois", 1, 60, False, False, 20),
    ("PVV3+", "PROLONGATION", "Priority 3-month extension", "Prolongation prioritaire 3 mois", 1, 90, False, False, 30),
    ("VV6", "PROLONGATION", "Visa Volant 6-month", "Visa Volant 6 mois", 90, 180, True, False, 40),
    ("VSR+", "PROLONGATION", "Regular stay extension", "Prolongation de séjour régulier", 1, 365, True, False, 50),
    ("VA", "AIRPORT", "Airport/Port Visa (7 days)", "Visa Aéroportuaire (7 jours)", 1, 7, False, False, 60),
    ("VVD", "VOYAGE", "Travel Visa", "Visa de Voyage", 28, 186, True, False, 70),
    ("VET", "ESTABLISHMENT", "Establishment Work Visa", "Visa d'Établissement Travail", 365, 731, True, True, 80),
    ("VEO", "ESTABLISHMENT", "Establishment Ordinary Visa", "Visa d'Établissement Ordinaire", 1000, 1150, True, False, 90),
    ("DT", "TRANSIT", "Disposition Transitoire", "Disposition Transitoire", 1, 15, False, False, 100),
    ("E-VVL", "ELECTRONIC", "E-Visa Volant", "E-Visa Volant", 1, 90, False, False, 110),
    ("E-VETS", "ELECTRONIC", "E-Visa Establishment", "E-Visa Établissement", 365, 730, True, True, 120),
    ("HOL-EX", "HOLIDAY", "Expat Holiday / Congé Visa", "Visa de Congé Expatrié", 1, 30, False, False, 130),
]


class Command(BaseCommand):
    help = "Seed the VisaTypeCatalog with official DRC visa codes."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for (code, category, name_en, name_fr, min_d, max_d,
             multiple, needs_carte, sort) in VISA_TYPES:

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
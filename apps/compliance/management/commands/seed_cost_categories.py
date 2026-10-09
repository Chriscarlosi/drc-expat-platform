"""Seed standard cost categories used by DRC mining HR teams."""

from django.core.management.base import BaseCommand
from apps.compliance.models import CostCategory


CATEGORIES = [
    ("VISA_FEE", "Visa fee", "Frais de visa", True, 10),
    ("CARTE_FEE", "Carte de Travail fee", "Frais de Carte de Travail", True, 20),
    ("DGM_PENALTY", "DGM overstay penalty", "Pénalité de dépassement DGM", True, 30),
    ("LEGAL_FEE", "Legal / notary fee", "Frais juridiques / notaire", True, 40),
    ("TRANSLATION", "Document translation", "Traduction de documents", True, 50),
    ("MEDICAL", "Medical exam", "Examen médical", True, 60),
    ("YELLOW_FEVER", "Yellow fever vaccination", "Vaccination fièvre jaune", True, 70),
    ("TRAVEL", "Travel / flight", "Voyage / vol", True, 80),
    ("AIRPORT_TAX", "Airport tax", "Taxe aéroportuaire", True, 90),
    ("ONEM_FEE", "ONEM registration", "Enregistrement ONEM", True, 100),
    ("OTHER", "Other", "Autre", True, 999),
]


class Command(BaseCommand):
    help = "Seed standard DRC cost categories."

    def handle(self, *args, **options):
        created = updated = 0
        for code, name_en, name_fr, billable, sort in CATEGORIES:
            obj, was_created = CostCategory.objects.update_or_create(
                code=code,
                defaults={
                    "name_en": name_en,
                    "name_fr": name_fr,
                    "is_billable": billable,
                    "sort_order": sort,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"✅ {code} — {name_en}"))
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created} created, {updated} updated. "
            f"Total categories: {CostCategory.objects.count()}"
        ))
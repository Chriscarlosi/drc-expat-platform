"""
Delete duplicate VisaRecord + CarteDeTravail rows.

IMPORTANT: visa_number and permit_number are EncryptedCharField.
The DB stores different ciphertext per row, so SQL grouping fails.
We must group in PYTHON where the field auto-decrypts.

Run: python manage.py purge_duplicate_visas [--dry-run]
"""

from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.visas.models import VisaRecord, CarteDeTravail


class Command(BaseCommand):
    help = "Delete duplicate VisaRecord and CarteDeTravail rows."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # ══════════════════════════════════════════════════════
        # VISAS
        # ══════════════════════════════════════════════════════
        self.stdout.write("\n═══ VISA RECORDS ═══")

        groups = defaultdict(list)
        for v in VisaRecord.objects.all().order_by("created_at"):
            key = v.visa_number  # decrypts in Python
            groups[key].append(v)

        v_deleted = 0
        for visa_number, records in groups.items():
            if len(records) <= 1:
                continue
            keep = records[0]
            to_del = records[1:]
            self.stdout.write(
                f"\n{visa_number}: {len(records)} copies. "
                f"Keep {keep.id}, delete {len(to_del)}."
            )
            for d in to_del:
                if dry_run:
                    self.stdout.write(f"  [DRY] Would delete {d.id}")
                else:
                    # Reassign prolongations to keeper first
                    try:
                        from apps.visas.models import VisaProlongation
                        VisaProlongation.objects.filter(parent_visa=d).update(parent_visa=keep)
                    except Exception:
                        pass
                    d.delete()
                    v_deleted += 1

        # ══════════════════════════════════════════════════════
        # CARTES DE TRAVAIL
        # ══════════════════════════════════════════════════════
        self.stdout.write("\n═══ CARTES DE TRAVAIL ═══")

        carte_groups = defaultdict(list)
        for c in CarteDeTravail.objects.all().order_by("created_at"):
            key = c.permit_number
            carte_groups[key].append(c)

        c_deleted = 0
        for permit_number, records in carte_groups.items():
            if len(records) <= 1:
                continue
            keep = records[0]
            to_del = records[1:]
            self.stdout.write(f"\n{permit_number}: {len(records)} copies.")
            for d in to_del:
                if dry_run:
                    self.stdout.write(f"  [DRY] Would delete {d.id}")
                else:
                    try:
                        from apps.visas.models import EstablishmentVisa
                        EstablishmentVisa.objects.filter(carte_de_travail=d).update(carte_de_travail=keep)
                    except Exception:
                        pass
                    d.delete()
                    c_deleted += 1

        # ══════════════════════════════════════════════════════
        # SUMMARY
        # ══════════════════════════════════════════════════════
        total_v = sum(len(g) - 1 for g in groups.values())
        total_c = sum(len(g) - 1 for g in carte_groups.values())

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n[DRY RUN] Would delete {total_v} visas + {total_c} cartes."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Deleted {v_deleted} visas + {c_deleted} cartes. "
                f"Visas remaining: {VisaRecord.objects.count()}, "
                f"Cartes remaining: {CarteDeTravail.objects.count()}"
            ))
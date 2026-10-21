"""
Delete duplicate ExpertProfile rows, keeping the OLDEST per (first_name, last_name).

Reassigns dependent records (cartes, visas, penalties, costs, documents)
from the duplicate to the keeper, THEN deletes the duplicate.

Run: python manage.py purge_duplicate_experts [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from django.db import transaction

from apps.experts.models import ExpertProfile


class Command(BaseCommand):
    help = "Delete duplicate experts, reassigning dependent records first."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        qs = ExpertProfile.objects.unscoped()

        duplicates = (
            qs.values("first_name", "last_name")
              .annotate(n=Count("id"), keep=Min("created_at"))
              .filter(n__gt=1)
        )

        if not duplicates:
            self.stdout.write(self.style.SUCCESS(
                "✅ No duplicates found. Nothing to clean up."
            ))
            return

        total_deleted = 0
        total_reassigned = 0

        for group in duplicates:
            fn = group["first_name"]
            ln = group["last_name"]

            all_matching = list(
                qs.filter(first_name=fn, last_name=ln).order_by("created_at")
            )
            keep = all_matching[0]
            to_delete = all_matching[1:]

            self.stdout.write(f"\n{fn} {ln}: {len(all_matching)} copies. "
                              f"Keeping (id={keep.id}), deleting {len(to_delete)}.")

            for dup in to_delete:
                if dry_run:
                    self.stdout.write(f"  [DRY RUN] Would delete: {dup.id}")
                    continue

                try:
                    with transaction.atomic():
                        reassigned = self._reassign_dependents(dup, keep)
                        dup.delete()
                        total_deleted += 1
                        total_reassigned += reassigned
                        self.stdout.write(
                            f"  ✓ Deleted {dup.id} (reassigned {reassigned} records)"
                        )
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠ Could not delete {dup.id}: {e}"
                    ))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n[DRY RUN] Would delete {sum(g['n'] - 1 for g in duplicates)} duplicates."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Deleted {total_deleted} duplicates, "
                f"reassigned {total_reassigned} dependent records. "
                f"Remaining experts: {qs.count()}"
            ))

    def _reassign_dependents(self, dup, keep) -> int:
        """Move all FK relationships from `dup` to `keep`. Returns count."""
        count = 0

        # ─── Direct foreign keys to ExpertProfile ────────────
        try:
            from apps.visas.models import CarteDeTravail, VisaRecord, VisaProlongation
            count += CarteDeTravail.objects.filter(expert=dup).update(expert=keep)
            count += VisaRecord.objects.filter(expert=dup).update(expert=keep)
            count += VisaProlongation.objects.filter(expert=dup).update(expert=keep)
        except Exception:
            pass

        try:
            from apps.compliance.models import PenaltyLedger, ExpertCost
            count += PenaltyLedger.objects.filter(expert=dup).update(expert=keep)
            count += ExpertCost.objects.filter(expert=dup).update(expert=keep)
        except Exception:
            pass

        # ─── UserCompanyMembership link (if any) ─────────────
        try:
            from apps.organization.models import UserCompanyMembership
            count += UserCompanyMembership.objects.filter(
                expert_profile=dup
            ).update(expert_profile=keep)
        except Exception:
            pass

        # ─── Generic-relationship: DocumentVersion ───────────
        try:
            from apps.documents.models import DocumentVersion
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(ExpertProfile)
            count += DocumentVersion.objects.filter(
                content_type=ct, object_id=str(dup.pk),
            ).update(object_id=str(keep.pk))
        except Exception:
            pass

        return count
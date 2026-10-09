"""Verify SHA-256 integrity of every document version."""

from django.core.management.base import BaseCommand

from apps.documents.models import DocumentVersion


class Command(BaseCommand):
    help = "Verify the SHA-256 integrity of every DocumentVersion file."

    def handle(self, *args, **options):
        total = DocumentVersion.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No document versions to verify."))
            return

        self.stdout.write(f"Verifying {total} document versions...\n")

        failures = []
        for v in DocumentVersion.objects.iterator():
            if not v.verify_integrity():
                failures.append(v)

        if failures:
            self.stdout.write(self.style.ERROR(
                f"\n❌ {len(failures)} file(s) failed integrity check:"
            ))
            for v in failures[:20]:
                self.stdout.write(self.style.ERROR(
                    f"   • {v.content_type.model} #{v.object_id} · "
                    f"{v.field_name} · v{v.version_number} · {v.sha256[:16]}…"
                ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS(
            f"✅ All {total} document versions verified. Chain of custody intact."
        ))
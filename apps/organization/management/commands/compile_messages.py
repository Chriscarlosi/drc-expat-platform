"""
Compile all locale/*/LC_MESSAGES/django.po → django.mo
Pure-Python — no GNU gettext needed on Windows.
"""

import polib
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compile .po translation files to .mo using polib."

    def handle(self, *args, **options):
        locale_dir = Path(settings.BASE_DIR) / "locale"
        if not locale_dir.exists():
            self.stdout.write(self.style.WARNING(f"No locale/ folder at {locale_dir}"))
            return

        compiled = 0
        for po_path in locale_dir.rglob("*.po"):
            mo_path = po_path.with_suffix(".mo")
            try:
                po = polib.pofile(str(po_path))
                po.save_as_mofile(str(mo_path))
                translated = sum(1 for e in po if e.translated())
                total = len(po)
                self.stdout.write(self.style.SUCCESS(
                    f"✅ {po_path.relative_to(settings.BASE_DIR)} → "
                    f"{mo_path.name} ({translated}/{total} translated)"
                ))
                compiled += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"❌ {po_path.relative_to(settings.BASE_DIR)} — {e}"
                ))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Compiled {compiled} file(s)."))
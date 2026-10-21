"""Seed default alert tiers (T-90/T-60/T-30 for all documents)."""

from django.core.management.base import BaseCommand
from apps.notifications.models import AlertTier


DEFAULTS = [
    (90, AlertTier.AppliesTo.ALL,   AlertTier.Channel.EMAIL, "T-90 (3 months) — all docs", 10),
    (60, AlertTier.AppliesTo.ALL,   AlertTier.Channel.EMAIL, "T-60 (2 months) — all docs", 20),
    (30, AlertTier.AppliesTo.ALL,   AlertTier.Channel.BOTH,  "T-30 (1 month) — email + SMS", 30),
    (14, AlertTier.AppliesTo.CARTE, AlertTier.Channel.BOTH,  "T-14 — Cartes urgent", 40),
    (7,  AlertTier.AppliesTo.VISA,  AlertTier.Channel.BOTH,  "T-7 — Visas urgent", 50),
]


class Command(BaseCommand):
    help = "Seed default AlertTier records."

    def handle(self, *args, **options):
        created = updated = 0
        for days, applies_to, channel, name, sort in DEFAULTS:
            obj, was_created = AlertTier.objects.update_or_create(
                threshold_days=days, applies_to=applies_to,
                defaults={
                    "name": name, "channel": channel,
                    "sort_order": sort, "is_active": True,
                },
            )
            created += was_created
            updated += (not was_created)
            self.stdout.write(self.style.SUCCESS(f"✅ T-{days} {applies_to} — {channel}"))
        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {created} created, {updated} updated. "
            f"Total tiers: {AlertTier.objects.count()}"
        ))
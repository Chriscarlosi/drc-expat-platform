"""Seed rotation schedules for existing experts (for demo)."""

import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.experts.models import ExpertProfile
from apps.travel.models import RotationSchedule


class Command(BaseCommand):
    help = "Seed rotation schedules for active experts."

    def handle(self, *args, **options):
        today = date.today()
        experts = ExpertProfile.objects.unscoped().filter(is_active=True)

        created = 0
        for e in experts:
            if RotationSchedule.objects.filter(expert=e).exists():
                continue

            pattern = random.choice([
                RotationSchedule.RotationPattern.R4_4,
                RotationSchedule.RotationPattern.R6_3,
                RotationSchedule.RotationPattern.R8_4,
                RotationSchedule.RotationPattern.R28_28,
            ])

            start = today - timedelta(days=random.randint(5, 60))

            RotationSchedule.objects.create(
                expert=e,
                pattern=pattern,
                cycle_start_date=start,
                is_active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Created {created} rotation schedules. "
            f"Total: {RotationSchedule.objects.count()}"
        ))
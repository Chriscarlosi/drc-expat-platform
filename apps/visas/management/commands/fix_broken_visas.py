"""
Fix broken seed data for VET visas.
Recalculates expiry to exactly 24 months from issue date.
Run: python manage.py fix_broken_visas
"""
from django.core.management.base import BaseCommand
from apps.visas.models import VisaRecord
from dateutil.relativedelta import relativedelta


class Command(BaseCommand):
    help = "Fix incorrect expiry dates for all VET seed records."

    def handle(self, *args, **options):
        # Find all VET visa records that are currently incorrect
        vet_visas = VisaRecord.objects.filter(visa_type__code='VET')

        fixed_count = 0
        for record in vet_visas:
            # Force exact 24 months based on issue date
            correct_expiry = record.issue_date + relativedelta(months=24)

            if record.expiry_date != correct_expiry:
                # Use .update() to bypass model validation for this data fix
                VisaRecord.objects.filter(pk=record.pk).update(expiry_date=correct_expiry)
                fixed_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Fixed {record.expert.full_name}: {record.visa_number} -> {correct_expiry}"
                ))

        if fixed_count == 0:
            self.stdout.write("No records needed fixing. All VET visas are correct.")
        else:
            self.stdout.write(self.style.SUCCESS(f"\nDone. Fixed {fixed_count} record(s)."))
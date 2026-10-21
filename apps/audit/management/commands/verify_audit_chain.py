"""Verify the integrity of the hash-chained audit log."""

import time

from django.core.management.base import BaseCommand

from apps.audit.models import ImmutableAuditLog, GENESIS_HASH


class Command(BaseCommand):
    help = "Verify the integrity of the hash-chained immutable audit log."

    def handle(self, *args, **options):
        start_time = time.time()   # ← START THE TIMER

        entries = list(ImmutableAuditLog.objects.order_by("sequence"))

        if not entries:
            self.stdout.write(self.style.WARNING("No audit entries to verify."))
            return

        self.stdout.write(f"Verifying {len(entries)} entries...\n")

        expected_prev = GENESIS_HASH
        expected_seq = 1
        errors = []

        for entry in entries:
            if entry.sequence != expected_seq:
                errors.append(f"[seq {entry.sequence}] expected sequence {expected_seq}")
            if entry.prev_hash != expected_prev:
                errors.append(
                    f"[seq {entry.sequence}] prev_hash mismatch "
                    f"(expected {expected_prev[:16]}…, got {entry.prev_hash[:16]}…)"
                )
            if not entry.verify():
                errors.append(f"[seq {entry.sequence}] HASH VERIFICATION FAILED.")
            expected_prev = entry.entry_hash
            expected_seq += 1

        duration_ms = int((time.time() - start_time) * 1000)

        # ── Save verification record (always, even on failure) ──
        from apps.audit.models import AuditChainCheck
        chain_head_for_record = entries[-1]
        AuditChainCheck.objects.create(
            is_valid=not errors,
            entry_count=len(entries),
            head_hash=chain_head_for_record.entry_hash,
            duration_ms=duration_ms,
        )

        if errors:
            self.stdout.write(self.style.ERROR(
                f"\n❌ INTEGRITY FAILURE — {len(errors)} issue(s):\n"
            ))
            for err in errors[:30]:
                self.stdout.write(self.style.ERROR(f"   • {err}"))
            raise SystemExit(1)

        chain_head = entries[-1]
        self.stdout.write(self.style.SUCCESS("✅ CHAIN INTACT — all entries verified."))
        self.stdout.write(f"   Total entries : {len(entries)}")
        self.stdout.write(f"   Head hash     : {chain_head.entry_hash}")
        self.stdout.write(f"   Head timestamp: {chain_head.timestamp}")
        self.stdout.write(f"   Duration      : {duration_ms} ms")
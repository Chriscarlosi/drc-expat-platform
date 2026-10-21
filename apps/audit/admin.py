import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin

from .models import ImmutableAuditLog
from ..visas.models import VisaRecord

@admin.register(ImmutableAuditLog)
class ImmutableAuditLogAdmin(ModelAdmin):
    """Read-only admin. No add, no change, no delete — by design."""

    list_display = (
        "sequence", "timestamp", "user_repr", "action",
        "model_name", "object_repr_short", "hash_preview", "chain_head_badge",
    )
    list_filter = ("action", "model_name", "timestamp")
    search_fields = ("user_repr", "model_name", "object_repr", "object_id")
    date_hierarchy = "timestamp"
    ordering = ("-sequence",)
    list_per_page = 100

    # We hide the raw 'changes' field and replace it with our custom method below
    exclude = ("changes",)

    def get_readonly_fields(self, request, obj=None):
        fields = [f.name for f in ImmutableAuditLog._meta.fields if f.name != "changes"]
        return tuple(fields) + ("changes_display",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Object")
    def object_repr_short(self, obj):
        return (obj.object_repr or "—")[:60]

    @admin.display(description="Hash")
    def hash_preview(self, obj):
        return format_html(
            '<code style="font-size:11px;color:#2A9D8F;">{}</code>',
            obj.entry_hash[:16] + "…" if obj.entry_hash else "—",
        )

    @admin.display(description="Chain")
    def chain_head_badge(self, obj):
        if obj.chain_head:
            return mark_safe(
                '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;'
                'border-radius:10px;font-size:10px;font-weight:700;">HEAD</span>'
            )
        return "—"

    @admin.display(description="Changes")
    def changes_display(self, obj):
        """Parse the JSON changes and render them as a premium HTML table."""
        if not obj.changes:
            return "—"

        try:
            # If it's already a dict (some Django versions auto-parse JSONField), use it.
            # Otherwise, parse it from a string.
            changes = obj.changes if isinstance(obj.changes, dict) else json.loads(obj.changes)
        except (ValueError, TypeError):
            return format_html('<pre style="font-size:11px; color:#64748b;">{}</pre>', str(obj.changes))

        if not changes:
            return "—"

        # Build the HTML table
        html = '<table style="width:100%; border-collapse:collapse; font-size:12px; margin-top:8px;">'
        html += '<thead><tr style="background:#f8fafc; border-bottom:1px solid #e2e8f0; text-align:left;">'
        html += '<th style="padding:8px; color:#64748b; font-weight:600;">Field</th>'
        html += '<th style="padding:8px; color:#64748b; font-weight:600;">Old Value</th>'
        html += '<th style="padding:8px; color:#64748b; font-weight:600;">New Value</th>'
        html += '</tr></thead><tbody>'

        for field, values in changes.items():
            # Django auditlog stores changes as a list: [old_value, new_value]
            old_val = values[0] if isinstance(values, list) and len(values) > 0 else "—"
            new_val = values[1] if isinstance(values, list) and len(values) > 1 else "—"

            # Format None values nicely
            old_display = "null" if old_val is None else str(old_val)
            new_display = "null" if new_val is None else str(new_val)

            # Color code: Red for old, Green for new
            html += '<tr style="border-bottom:1px solid #f1f5f9;">'
            html += f'<td style="padding:8px; font-weight:600; color:#334155;">{field}</td>'
            html += f'<td style="padding:8px; color:#dc2626; word-break:break-all;">{old_display}</td>'
            html += f'<td style="padding:8px; color:#16a34a; font-weight:500; word-break:break-all;">{new_display}</td>'
            html += '</tr>'

        html += '</tbody></table>'

        return mark_safe(html)


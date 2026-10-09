from django.contrib import admin
from django.utils.html import format_html

from .models import ImmutableAuditLog


@admin.register(ImmutableAuditLog)
class ImmutableAuditLogAdmin(admin.ModelAdmin):
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

    # All fields read-only
    readonly_fields = tuple(f.name for f in ImmutableAuditLog._meta.fields)

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
            obj.entry_hash[:16] + "…",
        )

    @admin.display(description="Chain")
    def chain_head_badge(self, obj):
        if obj.chain_head:
            return format_html(
                '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;'
                'border-radius:10px;font-size:10px;font-weight:700;">HEAD</span>'
            )
        return ""
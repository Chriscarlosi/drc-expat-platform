from django.contrib import admin
from django.utils.html import format_html

from .models import DocumentVersion


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):

    list_display = (
        "short_parent",
        "field_name",
        "version_badge",
        "uploaded_at",
        "uploaded_by_repr",
        "size_display",
        "hash_preview",
        "integrity_icon",
    )

    list_filter = ("field_name", "content_type", "uploaded_at")
    search_fields = ("object_id", "uploaded_by_repr", "original_filename", "sha256")
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)
    readonly_fields = tuple(f.name for f in DocumentVersion._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ─── Display methods ───────────────────────────────────

    @admin.display(description="Parent")
    def short_parent(self, obj):
        return f"{obj.content_type.model} #{obj.object_id}"

    @admin.display(description="Version")
    def version_badge(self, obj):
        color = "#2A9D8F" if obj.is_current else "#94A3B8"
        label = "CURRENT" if obj.is_current else "HISTORY"
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:12px;font-size:10px;font-weight:700;">v{} · {}</span>',
            color,
            obj.version_number,
            label,
        )

    @admin.display(description="Size")
    def size_display(self, obj):
        return f"{obj.file_size_bytes / 1024:.1f} KB"

    @admin.display(description="SHA-256")
    def hash_preview(self, obj):
        return format_html(
            '<code style="font-size:10px;color:#475569;">{}</code>',
            obj.sha256[:16] + "…",
        )

    @admin.display(description="Integrity")
    def integrity_icon(self, obj):
        if obj.verify_integrity():
            return format_html(
                '<span style="color:#2A9D8F;font-weight:800;">{}</span>',
                "✓ VERIFIED",
            )
        return format_html(
            '<span style="color:#E63946;font-weight:800;">{}</span>',
            "✗ TAMPERED",
        )
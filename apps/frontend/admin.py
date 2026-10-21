from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ("name", "company", "email", "status_badge", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "email", "company", "message")
    date_hierarchy = "created_at"
    readonly_fields = ("name", "email", "company", "phone", "role", "message",
                       "ip_address", "user_agent", "created_at")

    fieldsets = (
        ("Contact Information", {
            "fields": ("name", "email", "company", "phone", "role"),
        }),
        ("Message", {
            "fields": ("message",),
        }),
        ("Metadata", {
            "fields": ("status", "ip_address", "user_agent", "created_at"),
        }),
    )

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "NEW": "#3B82F6", "READ": "#F59E0B",
            "REPLIED": "#16A34A", "ARCHIVED": "#64748B",
        }
        color = colors.get(obj.status, "#64748B")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:700;">{}</span>',
            color, obj.get_status_display(),
        )
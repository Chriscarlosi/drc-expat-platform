from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AlertTier, AlertLog


@admin.register(AlertTier)
class AlertTierAdmin(ModelAdmin):
    list_display = (
        "name", "threshold_days", "channel", "applies_to",
        "is_active", "sort_order",
    )
    list_filter = ("channel", "applies_to", "is_active")
    search_fields = ("name",)
    ordering = ("-threshold_days",)


@admin.register(AlertLog)
class AlertLogAdmin(ModelAdmin):
    list_display = (
        "expert", "document_type", "threshold_days",
        "channel", "status", "sent_at",
    )
    list_filter = ("status", "channel", "document_type", "threshold_days")
    search_fields = ("expert__first_name", "expert__last_name", "recipients")
    date_hierarchy = "sent_at"
    readonly_fields = tuple(f.name for f in AlertLog._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import (
    PenaltyLedger,
    CostCategory,
    ExpertCost,
    MonthlyInvoice,
    ExportLog,
)


# ─── SUPER ADMIN ONLY MIXIN ───
class SuperAdminOnlyMixin:
    def has_module_permission(self, request): return request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_change_permission(self, request, obj=None): return request.user.is_superuser
    def has_add_permission(self, request): return request.user.is_superuser
    def has_delete_permission(self, request, obj=None): return request.user.is_superuser


# ═══════════════════════════════════════════════════════════════
#  PENALTY LEDGER
# ═══════════════════════════════════════════════════════════════

@admin.register(PenaltyLedger)
class PenaltyLedgerAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        "expert", "reason", "accrual_start_date",
        "days_overdue_display", "daily_rate_usd",
        "total_display", "resolved",
    )
    list_filter = ("reason", "resolved", "accrual_start_date")
    search_fields = ("expert__first_name", "expert__last_name")
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("expert",)

    @admin.display(description="Total USD")
    def total_display(self, obj):
        return format_html(
            '<strong style="color:#E63946;">${}</strong>',
            obj.total_amount_usd,
        )

    actions = ["mark_resolved"]

    @admin.action(description="Mark selected penalties as resolved")
    def mark_resolved(self, request, queryset):
        count = queryset.update(
            resolved=True,
            resolution_date=timezone.now().date(),
            resolution_notes=f"Resolved by {request.user} via admin",
        )
        self.message_user(request, f"✓ {count} penalty(ies) marked as resolved.")

    @admin.display(description="Days Overdue")
    def days_overdue_display(self, obj):
        days = obj.days_overdue
        if obj.resolved:
            return format_html('<span style="color:#2A9D8F;">Resolved</span>')
        if days >= 30:
            return format_html('<span style="color:#dc2626;font-weight:700;">{}d OVERDUE</span>', days)
        return format_html('<span style="color:#f59e0b;">{}d</span>', days)


# ═══════════════════════════════════════════════════════════════
#  COST CATEGORIES
# ═══════════════════════════════════════════════════════════════

@admin.register(CostCategory)
class CostCategoryAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = ("code", "name_en", "is_billable", "is_active", "sort_order")
    list_filter = ("is_billable", "is_active")
    search_fields = ("code", "name_en", "name_fr")
    ordering = ("sort_order", "code")


# ═══════════════════════════════════════════════════════════════
#  EXPERT COSTS
# ═══════════════════════════════════════════════════════════════

@admin.register(ExpertCost)
class ExpertCostAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        "expert", "category", "amount", "currency", "amount_usd",
        "incurred_date", "status", "invoice_number",
    )
    list_filter = ("category", "status", "currency", "incurred_date")
    search_fields = (
        "expert__first_name", "expert__last_name",
        "description", "invoice_number",
    )
    autocomplete_fields = ("expert", "category")
    readonly_fields = ("amount_usd", "created_at", "updated_at")
    date_hierarchy = "incurred_date"

    fieldsets = (
        ("Expert & Category", {
            "fields": ("expert", "category", "description"),
        }),
        ("Amount", {
            "fields": ("amount", "currency", "amount_usd"),
        }),
        ("Dates & Status", {
            "fields": ("incurred_date", "status", "invoice_number", "invoice_date"),
        }),
        ("Attachments", {
            "fields": ("receipt", "notes"),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
        }),
    )


# ═══════════════════════════════════════════════════════════════
#  MONTHLY INVOICES
# ═══════════════════════════════════════════════════════════════

@admin.register(MonthlyInvoice)
class MonthlyInvoiceAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        "invoice_number", "company", "period_label",
        "total_usd", "invoice_date", "due_date", "status",
    )
    list_filter = ("status", "company", "period_year", "period_month")
    search_fields = ("invoice_number", "company__name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at",)


# ═══════════════════════════════════════════════════════════════
#  EXPORT LOG — audit trail (read-only)
# ═══════════════════════════════════════════════════════════════

@admin.register(ExportLog)
class ExportLogAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        "user_repr", "format", "report_type", "row_count",
        "ip_address", "created_at",
    )
    list_filter = ("format", "report_type")
    search_fields = ("user_repr", "ip_address")
    date_hierarchy = "created_at"
    readonly_fields = tuple(f.name for f in ExportLog._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
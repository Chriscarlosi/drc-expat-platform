from django.contrib import admin
from django.utils.html import format_html
from .models import PenaltyLedger


@admin.register(PenaltyLedger)
class PenaltyLedgerAdmin(admin.ModelAdmin):
    list_display = (
        'expert', 'reason', 'accrual_start_date',
        'days_accrued', 'daily_rate_usd', 'total_display', 'resolved',
    )
    list_filter = ('reason', 'resolved', 'accrual_start_date')
    search_fields = ('expert__first_name', 'expert__last_name')
    readonly_fields = ('id', 'created_at')

    @admin.display(description='Total USD')
    def total_display(self, obj):
        return format_html(
            '<strong style="color:#c00;">${}</strong>', obj.total_amount_usd,
        )

    from .models import CostCategory, ExpertCost, MonthlyInvoice

    @admin.register(CostCategory)
    class CostCategoryAdmin(admin.ModelAdmin):
        list_display = ("code", "name_en", "is_billable", "is_active", "sort_order")
        list_filter = ("is_billable", "is_active")
        search_fields = ("code", "name_en", "name_fr")

    @admin.register(ExpertCost)
    class ExpertCostAdmin(admin.ModelAdmin):
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

    @admin.register(MonthlyInvoice)
    class MonthlyInvoiceAdmin(admin.ModelAdmin):
        list_display = (
            "invoice_number", "company", "period_label",
            "total_usd", "invoice_date", "due_date", "status",
        )
        list_filter = ("status", "company", "period_year", "period_month")
        search_fields = ("invoice_number", "company__name")
        autocomplete_fields = ("company",)
        readonly_fields = ("created_at",)
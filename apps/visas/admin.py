from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin

from .models import (
    CarteDeTravail,
    FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa,
    VisaTypeCatalog, VisaRecord, VisaProlongation,
)


# ─── SUPER ADMIN ONLY MIXIN ───
class SuperAdminOnlyMixin:
    def has_module_permission(self, request): return request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_change_permission(self, request, obj=None): return request.user.is_superuser
    def has_add_permission(self, request): return request.user.is_superuser
    def has_delete_permission(self, request, obj=None): return request.user.is_superuser


@admin.register(CarteDeTravail)
class CarteDeTravailAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = ("permit_number", "expert", "issue_date", "expiry_date", "expiry_status", "is_active")
    list_filter = ("is_active", "issuing_authority")
    search_fields = ("permit_number", "expert__first_name", "expert__last_name")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Expiry Status")
    def expiry_status(self, obj):
        days = obj.days_until_expiry
        if days < 0:
            return format_html('<span style="color:red;font-weight:bold;">{}</span>', "EXPIRED")
        if days < 60:
            return format_html('<span style="color:orange;">{} days left</span>', days)
        return format_html('<span style="color:green;">{} days</span>', days)


# ═══════════════════════════════════════════════════════════════
# LEGACY VISA ADMIN (Kept for compatibility)
# ═══════════════════════════════════════════════════════════════

class VisaAdminBase(SuperAdminOnlyMixin, ModelAdmin):
    list_display = ("visa_number", "expert", "issue_date", "expiry_date", "days_left_display", "status")
    list_filter = ("status",)
    search_fields = ("visa_number", "expert__first_name", "expert__last_name")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "issue_date"

    @admin.display(description="Days Left")
    def days_left_display(self, obj):
        days = obj.days_until_expiry
        if days < 0:
            return format_html('<span style="color:red;font-weight:bold;">{}</span>', "EXPIRED")
        if days < 30:
            return format_html('<span style="color:red;">{} days</span>', days)
        if days < 90:
            return format_html('<span style="color:orange;">{} days</span>', days)
        return format_html('<span style="color:green;">{} days</span>', days)


@admin.register(FlyingVisa)
class FlyingVisaAdmin(VisaAdminBase):
    list_display = VisaAdminBase.list_display + ("authorization_issued_date", "utilization_deadline", "arrived")


@admin.register(AirportVisa)
class AirportVisaAdmin(VisaAdminBase):
    list_display = VisaAdminBase.list_display + ("arrival_date", "hours_since_arrival", "is_in_critical_window")


@admin.register(VoyageVisa)
class VoyageVisaAdmin(VisaAdminBase):
    list_display = VisaAdminBase.list_display + ("entry_type",)


@admin.register(EstablishmentVisa)
class EstablishmentVisaAdmin(VisaAdminBase):
    list_display = VisaAdminBase.list_display + ("establishment_type", "compliance_flag")
    list_filter = VisaAdminBase.list_filter + ("establishment_type",)

    @admin.display(description="Compliance")
    def compliance_flag(self, obj):
        if obj.establishment_type != obj.EstablishmentType.WORK:
            return "—"
        if not obj.carte_de_travail:
            return format_html('<span style="color:red;font-weight:bold;">{}</span>', "NO PERMIT")
        if obj.carte_de_travail.expiry_date < obj.expiry_date:
            return format_html('<span style="color:orange;font-weight:bold;">{}</span>', "RISK")
        return format_html('<span style="color:green;">{}</span>', "OK")


# ═══════════════════════════════════════════════════════════════
# TICKET 5: VISA TYPE CATALOG ADMIN
# ═══════════════════════════════════════════════════════════════

@admin.register(VisaTypeCatalog)
class VisaTypeCatalogAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        "code", "name_en", "category", "validity_months",
        "extension_length_days", "allows_prolongation", "max_prolongations",
        "is_verified", "is_active"
    )
    list_filter = (
        "category", "is_active", "requires_carte_de_travail",
        "allows_prolongation", "must_exit_on_expiry", "is_verified"
    )
    search_fields = ("code", "name_en", "name_fr", "source_reference")

    fieldsets = (
        (None, {
            'fields': ('code', 'category', 'name_en', 'name_fr', 'description_en', 'description_fr')
        }),
        ('Validity & Prolongation Rules', {
            'fields': (
                'validity_months',
                'allows_prolongation',
                'max_prolongations',
                'must_exit_on_expiry',
                'extension_length_days',
                'min_validity_days',
                'max_validity_days'
            )
        }),
        ('Traceability & Verification', {
            'fields': ('is_verified', 'source_reference', 'source_date'),
            'description': 'Mark rules as Unverified until legally confirmed.'
        }),
        ('Other Rules', {
            'fields': ('allows_multiple_entries', 'requires_carte_de_travail', 'is_active', 'sort_order')
        }),
    )


# ═══════════════════════════════════════════════════════════════
# TICKET 6: VISA PROLONGATION INLINE & ADMIN WORKFLOW
# ═══════════════════════════════════════════════════════════════

class VisaProlongationInline(admin.TabularInline):
    """Inline to view the history of prolongations for a specific VisaRecord."""
    model = VisaProlongation
    extra = 0
    fields = ("prolongation_type", "status", "request_date", "old_expiry_date", "new_expiry_date", "approved_by")
    readonly_fields = ("old_expiry_date",)
    autocomplete_fields = ("prolongation_type", "approved_by")


@admin.register(VisaRecord)
class VisaRecordAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = ("visa_number", "expert", "visa_type", "issue_date", "expiry_date", "days_left_display", "status")
    list_filter = ("visa_type__category", "status")
    search_fields = ("visa_number", "expert__first_name", "expert__last_name")
    autocomplete_fields = ("expert", "visa_type")
    date_hierarchy = "issue_date"
    readonly_fields = ("created_at", "updated_at")
    inlines = [VisaProlongationInline]

    @admin.display(description="Days Left")
    def days_left_display(self, obj):
        days = obj.days_until_expiry
        if days < 0:
            return format_html('<span style="color:red;font-weight:bold;">{}</span>', "EXPIRED")
        if days < 30:
            return format_html('<span style="color:red;">{} days</span>', days)
        if days < 90:
            return format_html('<span style="color:orange;">{} days</span>', days)
        return format_html('<span style="color:green;">{} days</span>', days)


@admin.register(VisaProlongation)
class VisaProlongationAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        "prolongation_type", "expert", "parent_visa",
        "request_date", "status", "old_expiry_date",
        "new_expiry_date", "approved_by"
    )
    list_filter = ("status", "prolongation_type")
    search_fields = ("prolongation_number", "expert__first_name", "expert__last_name")
    autocomplete_fields = ("expert", "parent_visa", "prolongation_type", "approved_by")
    readonly_fields = ("created_at", "old_expiry_date")
    actions = ['approve_prolongations']

    @admin.action(description="Approve selected prolongations (Updates Parent Visa)")
    def approve_prolongations(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.status != VisaProlongation.Status.APPROVED:
                obj.status = VisaProlongation.Status.APPROVED
                obj.approved_by = request.user
                obj.approval_date = timezone.now().date()
                obj.save()
                count += 1

        self.message_user(request, f"{count} prolongation(s) approved successfully. Parent visas updated.")
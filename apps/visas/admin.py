from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CarteDeTravail,
    FlyingVisa, AirportVisa, VoyageVisa, EstablishmentVisa,
    VisaTypeCatalog, VisaRecord, VisaProlongation,
)


@admin.register(CarteDeTravail)
class CarteDeTravailAdmin(admin.ModelAdmin):
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


class VisaAdminBase(admin.ModelAdmin):
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


@admin.register(VisaTypeCatalog)
class VisaTypeCatalogAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "category", "min_validity_days", "max_validity_days", "requires_carte_de_travail", "is_active")
    list_filter = ("category", "is_active", "requires_carte_de_travail")
    search_fields = ("code", "name_en", "name_fr")


@admin.register(VisaRecord)
class VisaRecordAdmin(admin.ModelAdmin):
    list_display = ("visa_number", "expert", "visa_type", "issue_date", "expiry_date", "days_left_display", "status")
    list_filter = ("visa_type__category", "status")
    search_fields = ("visa_number", "expert__first_name", "expert__last_name")
    autocomplete_fields = ("expert", "visa_type")
    date_hierarchy = "issue_date"
    readonly_fields = ("created_at", "updated_at")

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
class VisaProlongationAdmin(admin.ModelAdmin):
    list_display = ("prolongation_type", "expert", "parent_visa", "request_date", "approval_date", "new_expiry_date")
    list_filter = ("prolongation_type",)
    search_fields = ("prolongation_number", "expert__first_name", "expert__last_name")
    autocomplete_fields = ("expert", "parent_visa")
    readonly_fields = ("created_at",)
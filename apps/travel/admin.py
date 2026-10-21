from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    CharterOperator, Aircraft, CharterRoute, CharterFlight,
    CharterPassenger, Dependant, RotationSchedule, TravelAuthorization,
)


# ═══════════════════════════════════════════════════════════════
# OPERATORS & AIRCRAFT
# ═══════════════════════════════════════════════════════════════

class AircraftInline(TabularInline):
    model = Aircraft
    extra = 0
    fields = (
        "registration", "model_name", "aircraft_type",
        "capacity_passengers", "has_medevac_config", "is_active",
    )


@admin.register(CharterOperator)
class CharterOperatorAdmin(ModelAdmin):
    list_display = ("code", "name", "operator_type", "iata_code", "is_active")
    list_filter = ("operator_type", "is_active")
    search_fields = ("code", "name", "iata_code", "icao_code")
    inlines = [AircraftInline]


@admin.register(Aircraft)
class AircraftAdmin(ModelAdmin):
    list_display = (
        "registration", "model_name", "operator",
        "capacity_passengers", "has_medevac_config", "is_active",
    )
    list_filter = ("operator", "aircraft_type", "is_active", "has_medevac_config")
    search_fields = ("registration", "model_name")
    autocomplete_fields = ("operator",)


# ═══════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════

@admin.register(CharterRoute)
class CharterRouteAdmin(ModelAdmin):
    list_display = (
        "origin_iata", "origin_name",
        "destination_iata", "destination_name",
        "typical_duration_minutes", "is_active",
    )
    list_filter = ("is_active",)
    search_fields = (
        "origin_iata", "origin_name",
        "destination_iata", "destination_name",
    )
    ordering = ("sort_order",)


# ═══════════════════════════════════════════════════════════════
# FLIGHTS
# ═══════════════════════════════════════════════════════════════

class CharterPassengerInline(TabularInline):
    model = CharterPassenger
    extra = 0
    fields = (
        "passenger_type", "expert", "dependant",
        "seat_number", "status", "ticket_cost_usd",
    )
    autocomplete_fields = ("expert", "dependant")


@admin.register(CharterFlight)
class CharterFlightAdmin(ModelAdmin):
    list_display = (
        "flight_number", "route", "operator", "departure_datetime",
        "status_display", "passenger_count_display",
        "dgm_badge", "medevac_badge",
        "manifest_download", "manifest_print_link",
    )
    list_filter = (
        "status", "operator", "route",
        "dgm_manifest_submitted", "medevac_ready",
    )
    search_fields = ("flight_number",)
    autocomplete_fields = ("operator", "aircraft", "route")
    date_hierarchy = "departure_datetime"
    inlines = [CharterPassengerInline]

    fieldsets = (
        ("Flight Details", {
            "fields": (
                "flight_number", "operator", "aircraft", "route",
                "departure_datetime", "arrival_datetime",
                "status", "seats_available",
            ),
        }),
        ("DGM Compliance", {
            "fields": ("dgm_manifest_submitted", "dgm_manifest_submitted_at"),
        }),
        ("Medevac", {
            "fields": ("medevac_ready",),
        }),
        ("Notes", {
            "fields": ("notes",),
        }),
    )

    @admin.display(description="Status")
    def status_display(self, obj):
        colors = {
            "SCHEDULED": "#3b82f6",
            "BOARDING": "#0d9488",
            "DEPARTED": "#0891b2",
            "ARRIVED": "#16a34a",
            "DELAYED": "#f59e0b",
            "CANCELLED": "#dc2626",
            "DIVERTED": "#9333ea",
            "MEDEVAC": "#dc2626",
        }
        color = colors.get(obj.status, "#64748b")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:700;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description="Pax")
    def passenger_count_display(self, obj):
        return obj.passenger_count

    @admin.display(description="DGM")
    def dgm_badge(self, obj):
        if obj.dgm_manifest_submitted:
            return format_html(
                '<span style="color:#16a34a;font-weight:700;">{}</span>',
                "✓ Filed",
            )
        return format_html(
            '<span style="color:#dc2626;font-weight:700;">{}</span>',
            "Pending",
        )

    @admin.display(description="Medevac")
    def medevac_badge(self, obj):
        if obj.medevac_ready:
            return format_html(
                '<span style="color:#16a34a;">{}</span>',
                "✓ Ready",
            )
        return "—"

    @admin.display(description="Manifest")
    def manifest_download(self, obj):
        return format_html(
            '<a href="/travel/flight/{}/manifest/" target="_blank" '
            'style="background:#0d9488;color:#fff;padding:4px 10px;'
            'border-radius:6px;font-size:11px;font-weight:700;'
            'text-decoration:none;">📄 DGM PDF</a>',
            obj.pk,
        )

    @admin.display(description="Print")
    def manifest_print_link(self, obj):
        return format_html(
            '<a href="/travel/flight/{}/manifest/print/" target="_blank" '
            'style="background:#3b82f6;color:#fff;padding:4px 10px;'
            'border-radius:6px;font-size:11px;font-weight:700;'
            'text-decoration:none;">🖨️ Print</a>',
            obj.pk,
        )


# ═══════════════════════════════════════════════════════════════
# PASSENGERS — separate admin (corrected list_display)
# ═══════════════════════════════════════════════════════════════

@admin.register(CharterPassenger)
class CharterPassengerAdmin(ModelAdmin):
    list_display = (
        "passenger_name", "passenger_type", "flight", "seat_number",
        "status", "ticket_cost_usd", "is_company_paid",
    )
    list_filter = ("passenger_type", "status", "is_company_paid")
    search_fields = (
        "booking_reference", "seat_number",
        "expert__last_name", "dependant__last_name",
    )
    autocomplete_fields = ("flight", "expert", "dependant")


# ═══════════════════════════════════════════════════════════════
# DEPENDANTS
# ═══════════════════════════════════════════════════════════════

@admin.register(Dependant)
class DependantAdmin(ModelAdmin):
    list_display = (
        "first_name", "last_name", "expert", "relationship",
        "date_of_birth", "nationality", "is_travel_eligible",
    )
    list_filter = ("relationship", "nationality", "is_travel_eligible")
    search_fields = ("first_name", "last_name", "expert__last_name")
    autocomplete_fields = ("expert",)
    date_hierarchy = "created_at"


# ═══════════════════════════════════════════════════════════════
# ROTATIONS
# ═══════════════════════════════════════════════════════════════

@admin.register(RotationSchedule)
class RotationScheduleAdmin(ModelAdmin):
    list_display = (
        "expert", "pattern", "cycle_start_date",
        "is_on_site_badge", "is_active",
    )
    list_filter = ("pattern", "is_active")
    search_fields = ("expert__first_name", "expert__last_name")
    autocomplete_fields = ("expert",)

    @admin.display(description="Currently")
    def is_on_site_badge(self, obj):
        on_site = obj.is_on_site
        if on_site is True:
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:2px 8px;'
                'border-radius:10px;font-size:11px;font-weight:700;">{}</span>',
                "ON SITE",
            )
        if on_site is False:
            return format_html(
                '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;'
                'border-radius:10px;font-size:11px;font-weight:700;">{}</span>',
                "OFF",
            )
        return "—"


# ═══════════════════════════════════════════════════════════════
# TRAVEL AUTHORIZATIONS
# ═══════════════════════════════════════════════════════════════

@admin.register(TravelAuthorization)
class TravelAuthorizationAdmin(ModelAdmin):
    list_display = (
        "request_number", "expert", "purpose",
        "requested_departure_date", "status_badge", "created_at",
    )
    list_filter = ("status", "purpose", "requested_departure_date")
    search_fields = (
        "request_number", "expert__first_name", "expert__last_name",
    )
    autocomplete_fields = ("expert", "route", "flight")
    filter_horizontal = ("accompanying_dependants",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at", "updated_at",
        "manager_approved_at", "hr_approved_at",
    )

    fieldsets = (
        ("Request", {
            "fields": (
                "request_number", "expert", "purpose",
                "route", "justification",
            ),
        }),
        ("Dates", {
            "fields": ("requested_departure_date", "requested_return_date"),
        }),
        ("Dependants", {
            "fields": ("accompanying_dependants",),
        }),
        ("Manager Approval", {
            "fields": ("manager_approved_by_repr", "manager_approved_at"),
        }),
        ("HR Approval", {
            "fields": ("hr_approved_by_repr", "hr_approved_at"),
        }),
        ("Outcome", {
            "fields": ("status", "rejection_reason", "flight"),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Status")
    def status_badge(self, obj):
        colors = {
            "DRAFT": "#64748b",
            "PENDING_MANAGER": "#f59e0b",
            "PENDING_HR": "#3b82f6",
            "APPROVED": "#16a34a",
            "REJECTED": "#dc2626",
            "CANCELLED": "#64748b",
            "COMPLETED": "#0d9488",
        }
        color = colors.get(obj.status, "#64748b")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:700;">{}</span>',
            color, obj.get_status_display(),
        )

    actions = ["approve_as_manager", "approve_as_hr", "reject_request"]

    @admin.action(description="✅ Approve as Manager (moves to HR)")
    def approve_as_manager(self, request, queryset):
        from django.utils import timezone
        count = 0
        for obj in queryset:
            if obj.status == TravelAuthorization.Status.PENDING_MANAGER:
                obj.status = TravelAuthorization.Status.PENDING_HR
                obj.manager_approved_by_id = request.user.id
                obj.manager_approved_by_repr = str(request.user)
                obj.manager_approved_at = timezone.now()
                obj.save()
                count += 1
        self.message_user(request, f"✅ {count} request(s) approved by Manager → now pending HR.")

    @admin.action(description="✅ Approve as HR (final approval)")
    def approve_as_hr(self, request, queryset):
        from django.utils import timezone
        count = 0
        for obj in queryset:
            if obj.status == TravelAuthorization.Status.PENDING_HR:
                obj.status = TravelAuthorization.Status.APPROVED
                obj.hr_approved_by_id = request.user.id
                obj.hr_approved_by_repr = str(request.user)
                obj.hr_approved_at = timezone.now()
                obj.save()
                count += 1
        self.message_user(request, f"✅ {count} request(s) approved by HR.")

    @admin.action(description="❌ Reject selected requests")
    def reject_request(self, request, queryset):
        count = queryset.update(
            status=TravelAuthorization.Status.REJECTED,
            rejection_reason=f"Rejected by {request.user} via admin",
        )
        self.message_user(request, f"❌ {count} request(s) rejected.")
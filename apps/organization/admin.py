from django.contrib import admin
from django.urls import path
from django.http import FileResponse, Http404
from pathlib import Path
from django.conf import settings
from unfold.admin import ModelAdmin

from .models import Company, Site, Department, UserCompanyMembership, WorkforceSnapshot


# ─── SUPER ADMIN ONLY MIXIN ───
class SuperAdminOnlyMixin:
    def has_module_permission(self, request): return request.user.is_superuser
    def has_view_permission(self, request, obj=None): return request.user.is_superuser
    def has_change_permission(self, request, obj=None): return request.user.is_superuser
    def has_add_permission(self, request): return request.user.is_superuser
    def has_delete_permission(self, request, obj=None): return request.user.is_superuser


class SiteInline(admin.TabularInline):
    model = Site
    extra = 0


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0


@admin.register(UserCompanyMembership)
class UserCompanyMembershipAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        "user", "company", "role", "department", "site",
        "is_default", "is_active",
    )
    list_filter = ("company", "role", "is_active", "department", "site")
    search_fields = ("user__username", "user__email", "company__name")
    autocomplete_fields = ("user", "company", "department", "site", "expert_profile")
    fieldsets = (
        ("Identity", {
            "fields": ("user", "company", "role", "expert_profile"),
        }),
        ("Scope (Department / Site Managers only)", {
            "fields": ("department", "site"),
            "description": (
                "Set department for Department Managers, site for Site Managers. "
                "Leave both blank for HR Managers / Admins (full company access)."
            ),
        }),
        ("Flags", {
            "fields": ("is_default", "is_active"),
        }),
    )


@admin.register(Company)
class CompanyAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = ("name", "slug", "congolese_staff_count", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "dgm_registration", "tax_id")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SiteInline, DepartmentInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Site)
class SiteAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = ("name", "company", "code", "province")
    list_filter = ("company", "province")
    search_fields = ("name", "code", "company__name")
    autocomplete_fields = ("company",)


@admin.register(Department)
class DepartmentAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = ("name", "company", "code")
    list_filter = ("company",)
    search_fields = ("name", "code", "company__name")
    autocomplete_fields = ("company",)


@admin.register(WorkforceSnapshot)
class WorkforceSnapshotAdmin(SuperAdminOnlyMixin, ModelAdmin):
    list_display = (
        'company', 'snapshot_date', 'total_congolese_staff',
        'total_expat_staff', 'total_workforce', 'expat_pct',
        'is_stale', 'created_by'
    )
    list_filter = ('company', 'snapshot_date')
    search_fields = ('company__name',)
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    date_hierarchy = 'snapshot_date'

    fieldsets = (
        (None, {
            'fields': ('company', 'snapshot_date', 'notes')
        }),
        ('Aggregate Totals', {
            'fields': ('total_congolese_staff', 'total_expat_staff')
        }),
        ('Congolese Breakdown', {
            'fields': ('congolese_class_i_v', 'congolese_supervisor', 'congolese_management')
        }),
        ('Expat Breakdown', {
            'fields': ('expat_class_i_v', 'expat_supervisor', 'expat_management')
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


# ─── CUSTOM ADMIN VIEWS ───
def download_procurement_pdf(request):
    """Serve the procurement PDF as a download."""
    path = Path(settings.MEDIA_ROOT) / "reports" / "DRC_Expat_Platform_Proposal.pdf"
    if not path.exists():
        raise Http404("PDF not yet generated. Run: python manage.py generate_procurement_pdf")
    return FileResponse(
        open(path, "rb"),
        as_attachment=True,
        filename="DRC_Expat_Platform_Proposal.pdf",
    )
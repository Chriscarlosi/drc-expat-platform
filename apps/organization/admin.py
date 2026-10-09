from django.contrib import admin
from .models import Company, Site, Department


class SiteInline(admin.TabularInline):
    model = Site
    extra = 0


class DepartmentInline(admin.TabularInline):
    model = Department
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "congolese_staff_count", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "dgm_registration")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SiteInline, DepartmentInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "province")
    list_filter = ("company", "province")
    search_fields = ("name", "code")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code")
    list_filter = ("company",)
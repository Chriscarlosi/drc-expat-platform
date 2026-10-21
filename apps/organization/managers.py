"""
Tenant-scoped model manager.

Every query automatically filters by the current tenant.
Call `.unscoped()` to bypass — use ONLY for cross-tenant reports.
"""

from __future__ import annotations

from django.db import models

from .context import get_current_tenant, is_bypass_enabled


class TenantQuerySet(models.QuerySet):
    """QuerySet that filters by the current tenant."""

    def unscoped(self) -> "TenantQuerySet":
        """Return the query WITHOUT tenant filtering.

        WARNING: use only for superuser reports, cross-tenant analytics,
        or background tasks that explicitly set a tenant.
        """
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, company) -> "TenantQuerySet":
        """Filter explicitly by the given company."""
        return self.filter(company=company)


class TenantManager(models.Manager.from_queryset(TenantQuerySet)):
    """
    Manager that auto-scopes queries to the current tenant + role scope.

    Behaviour:
        - Superuser (bypass) → no filter.
        - No tenant → empty queryset (fail-safe).
        - Department Manager → filter by department.
        - Site Manager → filter by site.
        - HR Manager / Admin / Owner → all records in the tenant.
    """

    def get_queryset(self) -> TenantQuerySet:
        from .context import (
            get_current_tenant, get_current_department,
            get_current_site, get_current_role, is_bypass_enabled,
        )
        from .models import UserCompanyMembership

        qs = super().get_queryset()

        if is_bypass_enabled():
            return qs

        tenant = get_current_tenant()
        if tenant is None:
            return qs.none()

        qs = qs.filter(company=tenant)

        role = get_current_role()
        if role == UserCompanyMembership.Role.DEPARTMENT_MANAGER:
            dept = get_current_department()
            if dept is not None:
                qs = qs.filter(department=dept)
            else:
                qs = qs.none()  # no scope assigned → safe empty
        elif role == UserCompanyMembership.Role.SITE_MANAGER:
            site = get_current_site()
            if site is not None:
                qs = qs.filter(site=site)
            else:
                qs = qs.none()

        return qs
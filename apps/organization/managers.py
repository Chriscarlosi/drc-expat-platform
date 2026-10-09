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
    Manager that auto-scopes queries to the current tenant.

    Behaviour:
        - If a tenant is set → filter by it.
        - If bypass is enabled (superuser, explicit opt-in) → no filter.
        - If no tenant is set and no bypass → return empty queryset.
          (This fails safe: unexpected queries don't leak data.)
    """

    def get_queryset(self) -> TenantQuerySet:
        qs = super().get_queryset()
        tenant = get_current_tenant()

        if tenant is None:
            if is_bypass_enabled():
                return qs
            return qs.none()

        return qs.filter(company=tenant)
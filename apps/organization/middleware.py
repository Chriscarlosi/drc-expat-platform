"""
Organization middleware.

Two middlewares:
  1. TenantContextMiddleware   — sets the current tenant for every request.
  2. MFAEnforcementMiddleware  — redirects staff users without a confirmed
                                 TOTP device to the MFA setup page.
"""

from __future__ import annotations

import logging

from .context import (
    set_current_tenant, reset_tenant,
    set_current_department, reset_department,
    set_current_site, reset_site,
    set_current_role, reset_role,
    set_bypass, reset_bypass,
)
from .models import UserCompanyMembership
from apps.audit.current_user import set_current_user, reset_current_user

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# TENANT CONTEXT MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

class TenantContextMiddleware:
    """
    Sets the current tenant + scope (department/site) for every request.

    Resolution order:
      1. Anonymous → no tenant.
      2. Superuser → bypass all filters.
      3. Otherwise → the user's default company membership, with
         department/site scopes if the role requires them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Declare all tokens upfront
        tenant_token = None
        dept_token = None
        site_token = None
        role_token = None
        bypass_token = None
        user_token = None

        # Read the request user FIRST
        user = getattr(request, "user", None)

        # Capture for audit signals (after `user` is defined)
        if user is not None and user.is_authenticated:
            user_token = set_current_user(user)
        else:
            user_token = set_current_user(None)

        # Resolve tenant
        if user is None or not user.is_authenticated:
            tenant_token = set_current_tenant(None)

        elif user.is_superuser:
            bypass_token = set_bypass(True)
            tenant_token = set_current_tenant(None)

        else:
            session_company_id = request.session.get("active_company_id")

            if session_company_id:
                membership = (
                    UserCompanyMembership.objects
                    .filter(user=user, company_id=session_company_id, is_active=True)
                    .select_related("company", "department", "site")
                    .first()
                )
            else:
                membership = (
                    UserCompanyMembership.objects
                    .filter(user=user, is_active=True)
                    .select_related("company", "department", "site")
                    .order_by("-is_default", "created_at")
                    .first()
                )

            if membership:
                request.active_company = membership.company
                request.active_company_role = membership.role
                request.active_department = membership.department
                request.active_site = membership.site

                tenant_token = set_current_tenant(membership.company)
                role_token = set_current_role(membership.role)

                if membership.role == UserCompanyMembership.Role.DEPARTMENT_MANAGER:
                    dept_token = set_current_department(membership.department)
                elif membership.role == UserCompanyMembership.Role.SITE_MANAGER:
                    site_token = set_current_site(membership.site)
            else:
                tenant_token = set_current_tenant(None)

        try:
            response = self.get_response(request)
        finally:
            for token, resetter in [
                (tenant_token, reset_tenant),
                (dept_token, reset_department),
                (site_token, reset_site),
                (role_token, reset_role),
                (bypass_token, reset_bypass),
                (user_token, reset_current_user),
            ]:
                if token is not None:
                    resetter(token)

        return response


# ═══════════════════════════════════════════════════════════════
# MFA ENFORCEMENT MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

class MFAEnforcementMiddleware:
    """
    Enforces MFA for high-privilege staff accounts only.

    Enforced: OWNER, ADMIN, HR_MANAGER
    Skipped:  EXECUTIVE, DEPARTMENT_MANAGER, SITE_MANAGER, EXPERT, VIEWER

    Non-staff users (is_staff=False) are also exempt.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        # Skip if not authenticated
        if not user or not user.is_authenticated:
            return self.get_response(request)

        # Superusers always get MFA
        if user.is_superuser:
            needs_mfa = True
        elif not user.is_staff:
            # Public-facing users (experts, GM) — no MFA
            needs_mfa = False
        else:
            # Check role to determine MFA requirement
            from .models import UserCompanyMembership

            MFA_ROLES = {
                UserCompanyMembership.Role.OWNER,
                UserCompanyMembership.Role.ADMIN,
                UserCompanyMembership.Role.HR_MANAGER,
            }

            has_privileged_role = UserCompanyMembership.objects.filter(
                user=user,
                is_active=True,
                role__in=MFA_ROLES,
            ).exists()

            needs_mfa = has_privileged_role

        if not needs_mfa:
            return self.get_response(request)

        # Check if they already have a confirmed MFA device
        from django_otp import devices_for_user
        devices = list(devices_for_user(user, confirmed=True))

        if devices:
            return self.get_response(request)

        # Whitelist paths that don't need MFA
        setup_url = "/admin/mfa-setup/"
        exempt_paths = (
            "/admin/mfa-setup/",
            "/admin/login/",
            "/admin/logout/",
            "/login/",
            "/logout/",
            "/static/",
            "/media/",
            "/favicon.ico",
            "/i18n/",
        )

        if request.path.startswith(exempt_paths):
            return self.get_response(request)

        # Enforce MFA
        from django.conf import settings
        if getattr(settings, "MFA_ENFORCED", True):
            from django.shortcuts import redirect
            return redirect(setup_url)

        return self.get_response(request)
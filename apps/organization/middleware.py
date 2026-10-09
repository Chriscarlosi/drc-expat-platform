"""
Middleware that sets the current tenant for every request.

Resolution order:
    1. If user is anonymous → no tenant.
    2. If user is superuser → bypass tenant filter (see everything).
    3. Otherwise → the user's default company membership.
"""

from __future__ import annotations

import logging

from .context import (
    set_current_tenant, reset_tenant,
    set_bypass, reset_bypass,
)
from .models import UserCompanyMembership

logger = logging.getLogger(__name__)


class TenantContextMiddleware:
    """Sets the current tenant based on the logged-in user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_token = None
        bypass_token = None

        user = getattr(request, "user", None)

        if user is None or not user.is_authenticated:
            # Anonymous — no tenant
            tenant_token = set_current_tenant(None)

        elif user.is_superuser:
            # Superusers see everything (for admin work)
            bypass_token = set_bypass(True)
            tenant_token = set_current_tenant(None)

        else:
            # Find the user's company. Use session override if present.
            session_company_id = request.session.get("active_company_id")

            if session_company_id:
                membership = UserCompanyMembership.objects.filter(
                    user=user,
                    company_id=session_company_id,
                    is_active=True,
                ).select_related("company").first()
            else:
                membership = UserCompanyMembership.objects.filter(
                    user=user, is_active=True,
                ).select_related("company").order_by("-is_default", "created_at").first()

            if membership:
                set_current_tenant(membership.company)
                request.active_company = membership.company
                request.active_company_role = membership.role
                tenant_token = set_current_tenant(membership.company)
            else:
                # User has no company assigned
                tenant_token = set_current_tenant(None)

        try:
            response = self.get_response(request)
        finally:
            if tenant_token is not None:
                reset_tenant(tenant_token)
            if bypass_token is not None:
                reset_bypass(bypass_token)

        return response

    class MFAEnforcementMiddleware:
        """
        Redirects users to the MFA setup page if:
          - They are staff (superuser or HR manager)
          - They don't have a TOTP device yet
          - They're not already on the MFA setup URL
        """

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            user = getattr(request, "user", None)

            if user and user.is_authenticated and user.is_staff:
                from django_otp import devices_for_user
                devices = list(devices_for_user(user, confirmed=True))

                # Skip if user has a confirmed device OR is already on setup page
                setup_url = "/admin/mfa-setup/"
                if not devices and not request.path.startswith(setup_url) and \
                        not request.path.startswith("/admin/login/") and \
                        not request.path.startswith("/static/") and \
                        not request.path.startswith("/media/"):

                    # But allow superuser to skip during dev — flip this flag later
                    from django.conf import settings
                    if getattr(settings, "MFA_ENFORCED", True):
                        from django.shortcuts import redirect
                        return redirect(setup_url)

            return self.get_response(request)
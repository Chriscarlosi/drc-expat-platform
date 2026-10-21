"""
Tenant context — stores the current tenant + scope for the active request.
"""

from __future__ import annotations

import contextvars
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Company, Department, Site

_current_tenant: contextvars.ContextVar[Optional["Company"]] = contextvars.ContextVar(
    "current_tenant", default=None,
)
_current_department: contextvars.ContextVar[Optional["Department"]] = contextvars.ContextVar(
    "current_department", default=None,
)
_current_site: contextvars.ContextVar[Optional["Site"]] = contextvars.ContextVar(
    "current_site", default=None,
)
_current_role: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_role", default=None,
)
_bypass_tenant_filter: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "bypass_tenant_filter", default=False,
)


# ─── Tenant ─────────────────────────────────────────────────
def set_current_tenant(company) -> contextvars.Token:
    return _current_tenant.set(company)


def get_current_tenant():
    return _current_tenant.get()


def reset_tenant(token: contextvars.Token) -> None:
    _current_tenant.reset(token)


# ─── Department scope ───────────────────────────────────────
def set_current_department(dept) -> contextvars.Token:
    return _current_department.set(dept)


def get_current_department():
    return _current_department.get()


def reset_department(token: contextvars.Token) -> None:
    _current_department.reset(token)


# ─── Site scope ─────────────────────────────────────────────
def set_current_site(site) -> contextvars.Token:
    return _current_site.set(site)


def get_current_site():
    return _current_site.get()


def reset_site(token: contextvars.Token) -> None:
    _current_site.reset(token)


# ─── Role ───────────────────────────────────────────────────
def set_current_role(role: str) -> contextvars.Token:
    return _current_role.set(role)


def get_current_role():
    return _current_role.get()


def reset_role(token: contextvars.Token) -> None:
    _current_role.reset(token)


# ─── Bypass ─────────────────────────────────────────────────
def set_bypass(value: bool) -> contextvars.Token:
    return _bypass_tenant_filter.set(value)


def is_bypass_enabled() -> bool:
    return _bypass_tenant_filter.get()


def reset_bypass(token: contextvars.Token) -> None:
    _bypass_tenant_filter.reset(token)
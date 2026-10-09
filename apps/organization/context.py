"""
Tenant context — stores the current tenant for the active request/task.

Uses contextvars (not threading.local) for async-safety.
"""

from __future__ import annotations

import contextvars
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Company


_current_tenant: contextvars.ContextVar[Optional["Company"]] = contextvars.ContextVar(
    "current_tenant", default=None,
)
_bypass_tenant_filter: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "bypass_tenant_filter", default=False,
)


def set_current_tenant(company: Optional["Company"]) -> contextvars.Token:
    """Set the tenant for the current request/task. Returns a token to reset."""
    return _current_tenant.set(company)


def get_current_tenant() -> Optional["Company"]:
    """Return the currently active tenant, or None."""
    return _current_tenant.get()


def reset_tenant(token: contextvars.Token) -> None:
    """Reset the tenant to its previous value."""
    _current_tenant.reset(token)


def set_bypass(value: bool) -> contextvars.Token:
    return _bypass_tenant_filter.set(value)


def is_bypass_enabled() -> bool:
    return _bypass_tenant_filter.get()


def reset_bypass(token: contextvars.Token) -> None:
    _bypass_tenant_filter.reset(token)
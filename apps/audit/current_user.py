"""Contextvar for the current request user (thread-safe)."""

from __future__ import annotations

import contextvars
from typing import Optional

_current_user: contextvars.ContextVar[Optional[object]] = contextvars.ContextVar(
    "current_user", default=None,
)


def set_current_user(user) -> contextvars.Token:
    return _current_user.set(user)


def get_current_user():
    return _current_user.get()


def reset_current_user(token: contextvars.Token) -> None:
    _current_user.reset(token)
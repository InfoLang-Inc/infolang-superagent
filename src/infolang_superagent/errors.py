"""Exceptions raised by ``infolang-superagent``.

Errors from the underlying ``infolang`` SDK (``infolang.errors.InfoLangError``)
and from Superagent (``superagent_ai.GuardError``) are left to propagate; this
module only covers configuration mistakes made when wiring the middleware up.
"""

from __future__ import annotations


class InfoLangSuperagentError(Exception):
    """Base class for every ``infolang-superagent`` error."""


class InfoLangSuperagentConfigError(InfoLangSuperagentError, ValueError):
    """Raised for invalid or missing configuration when constructing the middleware."""

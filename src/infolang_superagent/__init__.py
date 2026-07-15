"""InfoLang memory + Superagent safety middleware.

``SafeMemory`` wraps the InfoLang async memory client with Superagent's guard and
redact operations: PII is redacted before it is stored, and recalled context is
inject-scanned before it is returned.

Quickstart::

    from infolang_superagent import SafeMemory

    async with SafeMemory.from_api_keys(
        superagent_api_key="sk-...",
        infolang_api_key="il_live_...",
        namespace="user-42",
    ) as memory:
        # PII is redacted before it reaches /v1/remember
        await memory.remember("My email is john@example.com")

        # Each recalled chunk is scanned for prompt injection before use
        outcome = await memory.recall("what do you know about me?")
        for chunk in outcome.chunks:
            print(chunk.text)
"""

from __future__ import annotations

from ._version import __version__
from .errors import InfoLangSuperagentConfigError, InfoLangSuperagentError
from .middleware import (
    DEFAULT_FLAGGED_SOURCE,
    DEFAULT_FLAGGED_TAG,
    DEFAULT_SOURCE,
    SafeMemory,
)
from .types import (
    FlaggedChunk,
    GuardClient,
    RecallOutcome,
    RememberOutcome,
    TurnOutcome,
)

__all__ = [
    "__version__",
    "SafeMemory",
    "GuardClient",
    "RememberOutcome",
    "RecallOutcome",
    "TurnOutcome",
    "FlaggedChunk",
    "DEFAULT_SOURCE",
    "DEFAULT_FLAGGED_SOURCE",
    "DEFAULT_FLAGGED_TAG",
    "InfoLangSuperagentError",
    "InfoLangSuperagentConfigError",
]

"""Result types and the Superagent guard interface used by the middleware.

``GuardClient`` is a structural :class:`typing.Protocol` capturing just the two
Superagent operations the middleware calls (``guard`` and ``redact``). The real
``superagent_ai.Client`` satisfies it, and tests can supply a lightweight fake
with the same shape -- so the safety layer is mockable offline without a live
Superagent account.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from infolang.types import Chunk
from superagent_ai import GuardResult, RedactResult


class GuardClient(Protocol):
    """The subset of ``superagent_ai.Client`` the middleware depends on."""

    async def guard(self, text: str, /) -> GuardResult: ...

    async def redact(self, text: str, /) -> RedactResult: ...


@dataclass
class FlaggedChunk:
    """A recalled chunk that the guard flagged as unsafe to inject."""

    chunk: Chunk
    reason: str


@dataclass
class RememberOutcome:
    """Result of a safety-wrapped ``remember`` (redact -> store)."""

    memory_id: str | None
    namespace: str | None
    stored_text: str
    redacted: bool
    redaction_reasoning: str | None = None


@dataclass
class RecallOutcome:
    """Result of a safety-wrapped ``recall`` (retrieve -> inject-scan)."""

    chunks: list[Chunk]
    flagged: list[FlaggedChunk]
    namespace: str | None
    scanned: bool


@dataclass
class TurnOutcome:
    """Result of :meth:`SafeMemory.process_turn` for one conversational turn."""

    allowed: bool
    reasoning: str
    context: list[Chunk] = field(default_factory=list)
    flagged_context: list[FlaggedChunk] = field(default_factory=list)
    stored_id: str | None = None
    namespace: str | None = None
    flagged: bool = False

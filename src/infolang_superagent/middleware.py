"""``SafeMemory`` -- InfoLang memory behind a Superagent safety guard.

The middleware sits *in front of* InfoLang memory and applies Superagent's
guard/redact on the two dangerous edges:

* **write** (``remember``): PII is redacted *before* the text reaches
  ``/v1/remember``, so raw personal data never lands in a memory bank.
* **read** (``recall``): each recalled chunk is inject-scanned before it is
  handed back for prompting, so poisoned memories can be flagged/dropped instead
  of silently injected.

:meth:`SafeMemory.process_turn` ties these together for a single conversational
turn: guard the user input, recall prior context (scanned), and optionally
retain the (redacted) turn -- flagging turns the guard rejects.
"""

from __future__ import annotations

from typing import Any

from infolang import AsyncInfoLang
from superagent_ai import create_client

from .errors import InfoLangSuperagentConfigError
from .types import (
    FlaggedChunk,
    GuardClient,
    RecallOutcome,
    RememberOutcome,
    TurnOutcome,
)

DEFAULT_SOURCE = "superagent"
DEFAULT_FLAGGED_SOURCE = "superagent-flagged"
DEFAULT_FLAGGED_TAG = "flagged"


class SafeMemory:
    """Superagent-guarded wrapper around the async InfoLang memory client.

    Args:
        infolang: An :class:`infolang.AsyncInfoLang` client for the memory bank.
        guard: A Superagent guard client (``superagent_ai.Client`` or any object
            matching :class:`~infolang_superagent.types.GuardClient`).
        namespace: Default InfoLang bank (namespace) for calls that don't pass one.
        source: Default ``source`` tag written on stored memories.
        redact_before_store: Redact PII via Superagent before every ``remember``.
        scan_on_recall: Inject-scan each recalled chunk via Superagent.
        retain: Default for whether :meth:`process_turn` stores the turn.
        retain_flagged: When a turn is blocked, still store a redacted, tagged
            copy for audit.
        flagged_source: ``source`` tag used for blocked-turn audit records.
        flagged_tag: ``tags`` value used for blocked-turn audit records.
    """

    def __init__(
        self,
        infolang: AsyncInfoLang,
        guard: GuardClient,
        *,
        namespace: str | None = None,
        source: str = DEFAULT_SOURCE,
        redact_before_store: bool = True,
        scan_on_recall: bool = True,
        retain: bool = True,
        retain_flagged: bool = True,
        flagged_source: str = DEFAULT_FLAGGED_SOURCE,
        flagged_tag: str = DEFAULT_FLAGGED_TAG,
    ) -> None:
        self._il = infolang
        self._guard = guard
        self._namespace = namespace
        self._source = source
        self._redact_before_store = redact_before_store
        self._scan_on_recall = scan_on_recall
        self._retain = retain
        self._retain_flagged = retain_flagged
        self._flagged_source = flagged_source
        self._flagged_tag = flagged_tag
        self._owns_clients = False

    @classmethod
    def from_api_keys(
        cls,
        *,
        superagent_api_key: str,
        infolang_api_key: str | None = None,
        infolang_dev_key: str | None = None,
        superagent_base_url: str | None = None,
        base_url: str | None = None,
        namespace: str | None = None,
        workspace: str | None = None,
        **kwargs: Any,
    ) -> SafeMemory:
        """Build both clients from credentials and own their lifecycle.

        The returned instance owns the InfoLang and Superagent clients it creates;
        call :meth:`aclose` (or use ``async with``) to release them.
        """

        if not superagent_api_key:
            raise InfoLangSuperagentConfigError("superagent_api_key is required.")
        infolang = AsyncInfoLang(
            api_key=infolang_api_key,
            dev_key=infolang_dev_key,
            base_url=base_url,
            namespace=namespace,
            workspace=workspace,
        )
        guard = create_client(api_key=superagent_api_key, api_base_url=superagent_base_url)
        instance = cls(infolang, guard, namespace=namespace, **kwargs)
        instance._owns_clients = True
        return instance

    async def remember(
        self,
        text: str,
        *,
        namespace: str | None = None,
        tags: str | None = None,
        source: str | None = None,
    ) -> RememberOutcome:
        """Redact PII (unless disabled) and store the result in InfoLang."""

        ns = namespace or self._namespace
        if self._redact_before_store:
            redaction = await self._guard.redact(text)
            stored_text = redaction.redacted
            reasoning: str | None = redaction.reasoning
            redacted = True
        else:
            stored_text = text
            reasoning = None
            redacted = False
        result = await self._il.remember(
            stored_text, namespace=ns, source=source or self._source, tags=tags
        )
        return RememberOutcome(
            memory_id=result.memory_id,
            namespace=result.namespace or ns,
            stored_text=stored_text,
            redacted=redacted,
            redaction_reasoning=reasoning,
        )

    async def recall(
        self,
        query: str,
        *,
        namespace: str | None = None,
        top_k: int = 5,
        scan: bool | None = None,
    ) -> RecallOutcome:
        """Recall from InfoLang and inject-scan each chunk before returning it."""

        ns = namespace or self._namespace
        result = await self._il.recall(query, namespace=ns, top_k=top_k)
        scan_on = self._scan_on_recall if scan is None else scan
        result_ns = result.namespace or ns
        if not scan_on:
            return RecallOutcome(
                chunks=list(result.chunks), flagged=[], namespace=result_ns, scanned=False
            )
        safe: list[Any] = []
        flagged: list[FlaggedChunk] = []
        for chunk in result.chunks:
            verdict = await self._guard.guard(chunk.text)
            if verdict.rejected:
                flagged.append(FlaggedChunk(chunk=chunk, reason=verdict.reasoning))
            else:
                safe.append(chunk)
        return RecallOutcome(chunks=safe, flagged=flagged, namespace=result_ns, scanned=True)

    async def process_turn(
        self,
        user_input: str,
        *,
        namespace: str | None = None,
        top_k: int = 5,
        retain: bool | None = None,
    ) -> TurnOutcome:
        """Guard one turn, recall prior context, and optionally retain the turn.

        A rejected turn is not stored as normal memory; when ``retain_flagged`` is
        on, a redacted, tagged audit copy is stored and its id returned.
        """

        ns = namespace or self._namespace
        retain_on = self._retain if retain is None else retain
        verdict = await self._guard.guard(user_input)
        if verdict.rejected:
            stored_id: str | None = None
            if retain_on and self._retain_flagged:
                outcome = await self.remember(
                    user_input,
                    namespace=ns,
                    tags=self._flagged_tag,
                    source=self._flagged_source,
                )
                stored_id = outcome.memory_id
            return TurnOutcome(
                allowed=False,
                reasoning=verdict.reasoning,
                namespace=ns,
                stored_id=stored_id,
                flagged=True,
            )

        recalled = await self.recall(user_input, namespace=ns, top_k=top_k)
        stored_id = None
        if retain_on:
            outcome = await self.remember(user_input, namespace=ns)
            stored_id = outcome.memory_id
        return TurnOutcome(
            allowed=True,
            reasoning=verdict.reasoning,
            context=recalled.chunks,
            flagged_context=recalled.flagged,
            namespace=ns,
            stored_id=stored_id,
            flagged=False,
        )

    async def aclose(self) -> None:
        """Release the underlying clients, if this instance created them."""

        if not self._owns_clients:
            return
        await self._il.aclose()
        guard_aclose = getattr(self._guard, "aclose", None)
        if guard_aclose is not None:
            await guard_aclose()

    async def __aenter__(self) -> SafeMemory:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

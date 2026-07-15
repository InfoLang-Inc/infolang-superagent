from __future__ import annotations

import re
from typing import Any

import pytest
from infolang.types import Chunk, RecallResult, RememberResult
from superagent_ai import GuardResult, RedactResult

IL_BASE_URL = "https://api.test.infolang.ai"
SA_BASE_URL = "https://sa.test/api"

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class FakeAsyncInfoLang:
    """Async stand-in for ``infolang.AsyncInfoLang`` recording calls."""

    def __init__(self) -> None:
        self.remember_calls: list[dict[str, Any]] = []
        self.recall_calls: list[dict[str, Any]] = []
        self.closed = False
        self.recall_result = RecallResult(
            chunks=[Chunk(id="m1", text="Alice likes tea", score=0.9, tags=None)],
            namespace=None,
        )
        self.remember_result = RememberResult(id="mem-1", namespace=None)

    async def recall(
        self,
        query: str,
        *,
        namespace: str | None = None,
        top_k: int | None = None,
        **_: Any,
    ) -> RecallResult:
        self.recall_calls.append({"query": query, "namespace": namespace, "top_k": top_k})
        return self.recall_result

    async def remember(
        self,
        text: str,
        *,
        namespace: str | None = None,
        source: str | None = None,
        tags: str | None = None,
    ) -> RememberResult:
        self.remember_calls.append(
            {"text": text, "namespace": namespace, "source": source, "tags": tags}
        )
        return self.remember_result

    async def aclose(self) -> None:
        self.closed = True


class FakeGuard:
    """Async stand-in for ``superagent_ai.Client`` (guard + redact only).

    ``block_markers`` makes ``guard`` reject any input containing one of the
    markers (used to simulate prompt-injection detection). ``redact`` masks
    email addresses so tests can assert PII never reaches storage.
    """

    def __init__(self, *, block_markers: list[str] | None = None) -> None:
        self.block_markers = block_markers or []
        self.guard_calls: list[str] = []
        self.redact_calls: list[str] = []
        self.closed = False

    async def guard(self, text: str, /) -> GuardResult:
        self.guard_calls.append(text)
        rejected = any(marker in text for marker in self.block_markers)
        return GuardResult(
            rejected=rejected,
            reasoning="prompt-injection" if rejected else "ok",
            raw={},
            decision=None,
            usage=None,
        )

    async def redact(self, text: str, /) -> RedactResult:
        self.redact_calls.append(text)
        return RedactResult(
            redacted=_EMAIL_RE.sub("<REDACTED_EMAIL>", text),
            reasoning="redacted 1 entity" if _EMAIL_RE.search(text) else "no pii",
            raw={},
            usage=None,
        )

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def fake_il() -> FakeAsyncInfoLang:
    return FakeAsyncInfoLang()


@pytest.fixture
def fake_guard() -> FakeGuard:
    return FakeGuard()

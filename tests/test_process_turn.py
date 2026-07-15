from __future__ import annotations

from infolang.types import Chunk, RecallResult

from infolang_superagent import SafeMemory

from .conftest import FakeAsyncInfoLang, FakeGuard


async def test_allowed_turn_recalls_and_retains(fake_il: FakeAsyncInfoLang) -> None:
    fake_il.recall_result = RecallResult(
        chunks=[Chunk(id="c1", text="prior context", score=0.9, tags=None)],
        namespace="user-42",
    )
    guard = FakeGuard(block_markers=["ILLEGAL"])
    memory = SafeMemory(fake_il, guard, namespace="user-42")  # type: ignore[arg-type]

    outcome = await memory.process_turn("what's my plan? email me at a@b.com")

    assert outcome.allowed is True
    assert outcome.flagged is False
    assert [c.id for c in outcome.context] == ["c1"]
    assert outcome.stored_id == "mem-1"
    # Retained turn was redacted before storage.
    stored = fake_il.remember_calls[-1]
    assert "a@b.com" not in stored["text"]
    assert stored["source"] == "superagent"


async def test_blocked_turn_flags_and_audit_stores(fake_il: FakeAsyncInfoLang) -> None:
    guard = FakeGuard(block_markers=["ILLEGAL"])
    memory = SafeMemory(fake_il, guard, namespace="user-42")  # type: ignore[arg-type]

    outcome = await memory.process_turn("do something ILLEGAL with a@b.com")

    assert outcome.allowed is False
    assert outcome.flagged is True
    assert outcome.reasoning == "prompt-injection"
    assert outcome.context == []
    # A redacted, tagged audit copy was retained.
    assert outcome.stored_id == "mem-1"
    stored = fake_il.remember_calls[-1]
    assert stored["tags"] == "flagged"
    assert stored["source"] == "superagent-flagged"
    assert "a@b.com" not in stored["text"]
    # Blocked: we never recalled context for this turn.
    assert fake_il.recall_calls == []


async def test_blocked_turn_without_flag_retention(fake_il: FakeAsyncInfoLang) -> None:
    guard = FakeGuard(block_markers=["ILLEGAL"])
    memory = SafeMemory(
        fake_il,  # type: ignore[arg-type]
        guard,
        namespace="user-42",
        retain_flagged=False,
    )

    outcome = await memory.process_turn("ILLEGAL request")

    assert outcome.allowed is False
    assert outcome.stored_id is None
    assert fake_il.remember_calls == []


async def test_allowed_turn_retain_disabled(fake_il: FakeAsyncInfoLang) -> None:
    fake_il.recall_result = RecallResult(chunks=[], namespace="user-42")
    guard = FakeGuard()
    memory = SafeMemory(fake_il, guard, namespace="user-42", retain=False)  # type: ignore[arg-type]

    outcome = await memory.process_turn("benign question", retain=False)

    assert outcome.allowed is True
    assert outcome.stored_id is None
    assert fake_il.remember_calls == []  # nothing retained
    assert fake_il.recall_calls  # but context was still recalled

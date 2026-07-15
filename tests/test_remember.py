from __future__ import annotations

from infolang_superagent import SafeMemory

from .conftest import FakeAsyncInfoLang, FakeGuard


async def test_redacts_pii_before_store(
    fake_il: FakeAsyncInfoLang, fake_guard: FakeGuard
) -> None:
    memory = SafeMemory(fake_il, fake_guard, namespace="user-42")  # type: ignore[arg-type]
    outcome = await memory.remember("My email is john@example.com")

    # The text that reached InfoLang must be the redacted one.
    stored = fake_il.remember_calls[-1]
    assert stored["text"] == "My email is <REDACTED_EMAIL>"
    assert "john@example.com" not in stored["text"]
    assert stored["namespace"] == "user-42"
    assert stored["source"] == "superagent"

    assert outcome.redacted is True
    assert outcome.stored_text == "My email is <REDACTED_EMAIL>"
    assert outcome.memory_id == "mem-1"
    assert outcome.namespace == "user-42"
    assert outcome.redaction_reasoning == "redacted 1 entity"
    assert fake_guard.redact_calls == ["My email is john@example.com"]


async def test_redaction_can_be_disabled(
    fake_il: FakeAsyncInfoLang, fake_guard: FakeGuard
) -> None:
    memory = SafeMemory(fake_il, fake_guard, redact_before_store=False)  # type: ignore[arg-type]
    outcome = await memory.remember("raw john@example.com stays")

    assert fake_guard.redact_calls == []  # guard not consulted
    assert fake_il.remember_calls[-1]["text"] == "raw john@example.com stays"
    assert outcome.redacted is False
    assert outcome.redaction_reasoning is None


async def test_explicit_namespace_source_and_tags(
    fake_il: FakeAsyncInfoLang, fake_guard: FakeGuard
) -> None:
    memory = SafeMemory(fake_il, fake_guard, namespace="default-ns")  # type: ignore[arg-type]
    await memory.remember("note", namespace="other-ns", source="crm", tags="vip")

    stored = fake_il.remember_calls[-1]
    assert stored["namespace"] == "other-ns"
    assert stored["source"] == "crm"
    assert stored["tags"] == "vip"

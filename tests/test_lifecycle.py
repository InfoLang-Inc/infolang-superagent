from __future__ import annotations

import pytest

from infolang_superagent import InfoLangSuperagentConfigError, SafeMemory

from .conftest import FakeAsyncInfoLang, FakeGuard


def test_from_api_keys_requires_superagent_key() -> None:
    with pytest.raises(InfoLangSuperagentConfigError, match="superagent_api_key"):
        SafeMemory.from_api_keys(superagent_api_key="", infolang_api_key="il_live_x")


async def test_from_api_keys_builds_and_owns_clients() -> None:
    memory = SafeMemory.from_api_keys(
        superagent_api_key="sk-test",
        infolang_api_key="il_live_test",
        namespace="user-42",
        redact_before_store=False,
    )
    assert memory._owns_clients is True
    assert memory._namespace == "user-42"
    assert memory._redact_before_store is False  # forwarded kwarg
    # Closes the real (but unused) httpx-backed clients; no network involved.
    await memory.aclose()


async def test_aclose_is_noop_when_clients_not_owned(
    fake_il: FakeAsyncInfoLang, fake_guard: FakeGuard
) -> None:
    memory = SafeMemory(fake_il, fake_guard)  # type: ignore[arg-type]
    await memory.aclose()
    assert fake_il.closed is False
    assert fake_guard.closed is False


async def test_context_manager_closes_owned_clients(
    fake_il: FakeAsyncInfoLang, fake_guard: FakeGuard
) -> None:
    memory = SafeMemory(fake_il, fake_guard)  # type: ignore[arg-type]
    memory._owns_clients = True
    async with memory as m:
        assert m is memory
    assert fake_il.closed is True
    assert fake_guard.closed is True


async def test_aclose_tolerates_guard_without_aclose(fake_il: FakeAsyncInfoLang) -> None:
    class GuardNoClose:
        async def guard(self, text: str, /):  # pragma: no cover - not called here
            raise NotImplementedError

        async def redact(self, text: str, /):  # pragma: no cover - not called here
            raise NotImplementedError

    memory = SafeMemory(fake_il, GuardNoClose())  # type: ignore[arg-type]
    memory._owns_clients = True
    await memory.aclose()  # must not raise even though guard has no aclose()
    assert fake_il.closed is True

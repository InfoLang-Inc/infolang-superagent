"""Optional live smoke test against the real InfoLang and Superagent APIs.

Skipped unless both ``INFOLANG_API_KEY`` and ``SUPERAGENT_API_KEY`` are set --
NOT part of the default ``pytest`` run and excluded from the coverage gate. It
only touches banks prefixed ``superagent-ittest-`` and forgets what it stores in
a ``finally`` block, so it is safe against a shared account.

Run it with::

    INFOLANG_API_KEY=il_live_... SUPERAGENT_API_KEY=sk-... \
        pytest tests/test_live_smoke.py -v
"""

from __future__ import annotations

import os
import uuid

import pytest

from infolang_superagent import SafeMemory

pytestmark = pytest.mark.skipif(
    not (os.environ.get("INFOLANG_API_KEY") and os.environ.get("SUPERAGENT_API_KEY")),
    reason="live smoke test requires INFOLANG_API_KEY and SUPERAGENT_API_KEY",
)


async def test_live_redact_store_recall() -> None:
    namespace = f"superagent-ittest-{uuid.uuid4().hex[:8]}"
    memory = SafeMemory.from_api_keys(
        superagent_api_key=os.environ["SUPERAGENT_API_KEY"],
        infolang_api_key=os.environ["INFOLANG_API_KEY"],
        namespace=namespace,
    )
    stored_id: str | None = None
    try:
        outcome = await memory.remember("Contact me at live-smoke@example.com about Orchid")
        stored_id = outcome.memory_id
        assert outcome.redacted is True
        assert "live-smoke@example.com" not in outcome.stored_text

        recalled = await memory.recall("what is my contact info?", top_k=5)
        assert recalled.scanned is True
    finally:
        if stored_id:
            await memory._il.forget(stored_id, namespace=namespace)
        await memory.aclose()

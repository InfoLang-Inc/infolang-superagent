"""A minimal safety-wrapped memory loop.

Redacts PII before storing each turn and inject-scans recalled context before
using it. Requires real credentials and network.

    INFOLANG_API_KEY=il_live_... SUPERAGENT_API_KEY=sk-... python examples/safe_chatbot.py
"""

from __future__ import annotations

import asyncio
import os


async def main() -> None:
    from infolang_superagent import SafeMemory

    async with SafeMemory.from_api_keys(
        superagent_api_key=os.environ["SUPERAGENT_API_KEY"],
        infolang_api_key=os.environ["INFOLANG_API_KEY"],
        namespace="demo-user",
    ) as memory:
        turn = await memory.process_turn("Remember my email is jane@example.com")
        print("allowed:", turn.allowed, "| stored:", turn.stored_id)

        recalled = await memory.recall("what is my email?")
        for chunk in recalled.chunks:
            print("context:", chunk.text)  # already redacted at write time
        for flagged in recalled.flagged:
            print("flagged (not injected):", flagged.reason)


if __name__ == "__main__":
    asyncio.run(main())

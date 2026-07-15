# infolang-superagent

InfoLang semantic memory behind a [Superagent](https://superagent.sh) safety
guard. The middleware sits *in front of* [InfoLang](https://infolang.ai) memory
and applies Superagent on the two dangerous edges:

- **write** — PII is **redacted before** the text reaches `/v1/remember`, so raw
  personal data never lands in a memory bank.
- **read** — each recalled chunk is **inject-scanned** before it is returned, so
  a poisoned memory can be flagged/dropped instead of silently injected into a
  prompt.

> **Language decision.** Superagent ships both a Python and a TypeScript SDK
> (both published as `superagent-ai`). This package is **Python**, matching the
> published InfoLang Python SDK (`infolang>=0.2,<0.3`, PyPI). The extension point
> used here is Superagent's client API — async `Client.guard(...)` and
> `Client.redact(...)` — verified against the **installed** `superagent-ai`
> (`0.0.23`: `superagent_ai.create_client`, `GuardResult`, `RedactResult`), not
> assumed from docs.

## Install

The InfoLang Python SDK is not yet on PyPI. Until it is, install it from source
alongside this package:

```bash
pip install "infolang @ git+ssh://git@github.com/InfoLang-Inc/infolang-sdk-python.git@v0.2.0"
pip install infolang-superagent
```

For local development against this repo:

```bash
pip install -e ".[dev]"
pip install -e "../sdk-python"   # editable InfoLang SDK, local testing only
```

## Quickstart

```python
from infolang_superagent import SafeMemory

async with SafeMemory.from_api_keys(
    superagent_api_key="sk-...",
    infolang_api_key="il_live_...",
    namespace="user-42",
) as memory:
    # PII is redacted before it reaches /v1/remember.
    await memory.remember("My email is john@example.com")

    # Recalled context is inject-scanned before you use it.
    outcome = await memory.recall("what do you know about me?")
    for chunk in outcome.chunks:        # safe chunks
        print(chunk.text)
    for flagged in outcome.flagged:     # dropped, with a reason
        print("blocked:", flagged.reason)
```

You can also inject pre-built clients (e.g. to share an `httpx` pool or a fake in
tests):

```python
from infolang import AsyncInfoLang
from superagent_ai import create_client
from infolang_superagent import SafeMemory

memory = SafeMemory(
    AsyncInfoLang(api_key="il_live_..."),
    create_client(api_key="sk-..."),
    namespace="user-42",
)
```

## API

`SafeMemory(infolang, guard, *, namespace=None, source="superagent", redact_before_store=True, scan_on_recall=True, retain=True, retain_flagged=True, ...)`

| Method | What it does |
|---|---|
| `remember(text, *, namespace, tags, source)` | Redact (unless disabled) → store. Returns a `RememberOutcome` with the `stored_text` actually written. |
| `recall(query, *, namespace, top_k, scan)` | Recall → inject-scan each chunk. Returns a `RecallOutcome` with `chunks` (safe) and `flagged`. |
| `process_turn(user_input, *, namespace, top_k, retain)` | Guard the turn → recall prior context → retain (redacted). Blocked turns are `flagged` and (optionally) stored as a redacted audit copy. Returns a `TurnOutcome`. |
| `aclose()` / `async with` | Releases clients created by `from_api_keys`. |

## Workspace vs namespace

InfoLang has two scoping levels; this package passes both straight through to the
`infolang` client:

- **workspace = tenant.** Pass `workspace=` to `from_api_keys` (sent as the
  `X-InfoLang-Workspace-Id` header) to select an account workspace.
- **namespace = memory bank.** A managed API key honours the `namespace` on both
  reads and writes; a dev key is namespace-pinned by the key itself. Set a
  default `namespace=` and/or override per call.

## Security / privacy

- **Public surfaces only.** InfoLang is reached exclusively through the published
  `infolang` SDK (public `il-runtime` REST contract); Superagent through its
  published `superagent-ai` SDK. No runtime, engine, or model internals.
- **Redact before store is the point.** With `redact_before_store=True` (default)
  the *redacted* string is what gets persisted — verified end-to-end in
  `tests/test_end_to_end.py` by reading the stored record back.
- **Inject-scan before use.** Recalled chunks that the guard rejects are returned
  under `flagged`, never mixed into `chunks`.

## Testing

```bash
pip install -e ".[dev]"
pip install -e "../sdk-python"
ruff check .
mypy
pytest
```

Tests run fully offline: the InfoLang and Superagent clients are faked for unit
tests, and the end-to-end tests drive the *real* SDKs against a `respx`-mocked
HTTP layer — no network and no API keys required. Coverage gate: 90%
(`--cov-fail-under=90`). An optional live round-trip lives in
`tests/test_live_smoke.py`, gated on `INFOLANG_API_KEY` + `SUPERAGENT_API_KEY`.

See `examples/safe_chatbot.py` for a runnable turn loop.

## License

Apache-2.0

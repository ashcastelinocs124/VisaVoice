# Short-term Memory

## Recent tasks (newest first, keep at most 5)

### 2026-04-19 — Task 16: Tool-call contract tests
- Wrote `tests/agent/test_tool_contracts.py` with 3 live-model tests against `gpt-4.1-mini`, module-skipped when `OPENAI_API_KEY` is absent.
- Tests cover: FAQ intent → `lookup_faq`, verified booking intent → `book_appointment`, unverified booking request → `verify_identity` first.
- With key set: 1/3 passed (faq), 2/3 failed (booking paths returned clarifying text, `tool_calls=None`). Spec explicitly accepts either outcome.
- Commit: `de9de46` (test: tool-call contract tests against gpt-4.1-mini).
- Follow-up captured in learnings.md: real contract tests should use the production `SYSTEM_PROMPT` (Task 14) rather than a stripped-down `SYS`.

### 2026-04-19 — Task 15: HTTP tool wrappers
- Created `src/visavoice/agent/tools.py` with `ToolClient` async wrapper over `httpx.AsyncClient`.
- Four tools: `lookup_faq`, `verify_identity`, `book_appointment`, `escalate_to_human`.
- `_post()` helper returns typed error dicts on `TimeoutException` (`reason="timeout"`), `ConnectError` (`"backend_down"`), `HTTPStatusError` (`"http_{code}"`). 3.0s default timeout. Callers never need try/except.
- Wrote `tests/agent/test_tools.py` with 5 tests via `pytest-httpx` `httpx_mock` — happy paths for all 4 tools + timeout-becomes-typed-error.
- No `pytest.ini` or config change needed; `httpx_mock` autoloaded under existing `asyncio_mode = "auto"`.
- Commit: `b83f9e3` (feat: HTTP tool wrappers with typed error fallbacks).

### 2026-04-19 — Task 14: Prompts module
- `src/visavoice/agent/prompts.py` with `SYSTEM_PROMPT` (readback-before-verify, names 4 tools, prompt-injection refusal, English-only, no legal advice) + `CONFIRMATION_TEMPLATES` for `uin_dob` and `booking`.
- 4 tests pass. Commit: `64bb699`.

### 2026-04-19 — Task 13: Safety classifier
- Added `make_openai_classifier(api_key, model="gpt-4.1-mini")` to `src/visavoice/agent/safety.py`. AsyncOpenAI, 0.5s timeout, JSON-object response_format, conservative system prompt.
- Scanner.scan already handled regex-wins, classifier-hit, classifier-miss, classifier-exception; no scan-logic changes needed.
- 4 tests pass. Commit: `3779ac2`.

### 2026-04-19 — Task 12: Safety regex layer
- `src/visavoice/agent/safety_patterns.py` ships 8 precompiled regexes across self_harm_ideation (×2), sevis_termination, ice_contact, police_contact, abuse, acute_medical, deportation_threat.
- `src/visavoice/agent/safety.py` has `Scanner.scan_sync`/`scan`, `ScanResult`, SCRIPTS map, HIGH_SEVERITY set.
- 17 parametrized tests (8 HITS + 9 MISSES) pass on first run. Commit: `af86e3c`.

## Current state
- Branch: `feat/v0`.
- Tests: 59 passing (excluding `test_tool_contracts.py`), 60 passing + 2 failing when contract tests are included with `OPENAI_API_KEY` set. Task spec accepts either outcome for contract tests.
- Next up: Task 17 (agent entrypoint / LiveKit worker), then Task 24 (CI).

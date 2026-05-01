# visavoice

A voice-based AI receptionist for Uni International Offices. International students dial a phone number and talk to an AI that answers common immigration-related questions, books advising appointments, and safely hands off to humans when the situation calls for it.

> **Status:** v0 code complete on `main`. 62 tests passing, CI green. Deploy + telephony wiring (Fly.io, Twilio DID, LiveKit SIP trunk) not yet done — credentials required.

---

## Why this exists

ISSS offices handle a mix of call types with very different costs:
- **High-volume, low-complexity:** "when can I apply for OPT?" "do I need a travel signature?" "how do I update my address?" These are policy questions with stable, documented answers, and they drown staff.
- **Appointment logistics:** booking, rescheduling, cancelling general advising slots.
- **Advisor-specific or sensitive:** SEVIS termination, deportation fears, mental-health distress, abuse disclosure. These need humans — immediately and correctly.

A traditional phone tree either mishandles the first category (long menus, no natural language) or dangerously mishandles the third (wrong routing on a crisis call). visavoice splits the problem: the AI handles what it's demonstrably good at, and a hardened safety layer forces human handoff for anything that isn't.

## What v0 does

| Capability | v0 | Target |
|---|---|---|
| Answer common ISSS questions | ✅ 3 curated FAQs (OPT basics, travel signature, address change) | Hybrid: curated for policy-sensitive, RAG for the long tail |
| Book advising appointments | ✅ single type, mock in-memory scheduler | Real iSTART/Sunapsis integration |
| Verify student identity | ✅ spoken UIN + DOB (matches current receptionist practice) | Tiered by risk; SSO handoff for SEVIS-sensitive actions |
| Route to the right human | ✅ ticket file written on escalation | Warm transfer via SIP REFER or Twilio dial verb |
| Escalate distress to a crisis line | ✅ regex + classifier safety layer, scripted crisis referrals, call terminates automatically | Same model, expanded category list |
| Languages | English only | English + Mandarin + Hindi |
| Retention | 7 days for metadata; no audio, no transcripts | 30 days with redaction and DPA |

## Architecture

```
Student phone ──► Twilio DID ──► LiveKit Cloud SIP ──► Agent worker
                                                         │
                                                         ├── OpenAI Realtime  (gpt-realtime, voice=alloy)
                                                         │     speech-to-speech; 4 registered tools
                                                         │
                                                         ├── Safety scanner   (runs in parallel on every
                                                         │     finalised user transcript)
                                                         │       ├── Regex layer  (sub-ms, non-negotiable)
                                                         │       └── gpt-4.1-mini classifier (fail-open)
                                                         │
                                                         └── ToolClient  ──► FastAPI backend (localhost)
                                                                              ├── /faq/lookup
                                                                              ├── /identity/verify
                                                                              ├── /appointments
                                                                              └── /escalation
```

**Key design properties:**

1. **The safety scanner runs in parallel with the model, not before it.** Running it first would add latency to every turn; running it in parallel means the happy path is free and only a hit pays the interrupt cost. On a hit, `session.interrupt()` cancels the LLM mid-word, a **hardcoded** scripted line is played (not generated), an escalation ticket is written, and the call ends — even if the model would have kept talking.
2. **Every state change goes through HTTP to the FastAPI backend.** The agent holds no booking state. This means the v1 switch to real iSTART is a drop-in swap of `/appointments`, not a refactor.
3. **No secrets over the model.** Tools are the only path to state change. The system prompt explicitly refuses instruction-override attempts. Identity verification requires spoken read-back and is rate-limited per call.
4. **Defense in depth on safety.** The model has its own `escalate_to_human` tool *and* the scanner hook runs regardless of what the model decides. Regex is the guarantee; the classifier is additive.

Full details in `docs/plans/2026-04-19-visavoice-design.md`.

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | |
| Package manager | `uv` | Hatchling build backend for `src/` layout |
| Telephony (PSTN) | Twilio | Inbound DID, SIP trunk to LiveKit |
| Real-time orchestration | LiveKit Agents 1.5.4 | Worker dispatched per call, handles VAD + barge-in |
| Voice model | OpenAI Realtime (`gpt-realtime`, voice `alloy`) | Speech-to-speech, English only in v0 |
| Safety classifier | OpenAI `gpt-4.1-mini` | 0.5s timeout; failures are treated as non-hit (regex is the guarantee) |
| FAQ embeddings | OpenAI `text-embedding-3-small` | Cosine similarity, threshold 0.7 |
| Backend | FastAPI + Pydantic | Runs in-process with the agent worker via supervisord |
| Storage | Flat JSON files with atomic writes (`tempfile` + `os.rename`) | No database in v0 |
| Tests | pytest + pytest-asyncio + pytest-httpx | TDD on everything except the LiveKit integration layer |
| CI | GitHub Actions | Lint (ruff), types (pyright), unit tests. Contract tests gated on `OPENAI_API_KEY` secret. |
| Deploy (planned) | Fly.io, single region `ord` | One container running agent + backend via supervisord |

## Project structure

```
visavoice/
├── src/visavoice/
│   ├── config.py                 # env-backed Settings dataclass
│   ├── agent/
│   │   ├── main.py               # LiveKit worker entrypoint
│   │   ├── prompts.py            # system prompt + confirmation templates
│   │   ├── safety.py             # Scanner + SCRIPTS + classifier factory
│   │   ├── safety_patterns.py    # regex patterns (precision-first)
│   │   └── tools.py              # ToolClient — HTTP wrapper over backend
│   └── backend/
│       ├── __main__.py           # uvicorn entrypoint
│       ├── app.py                # FastAPI create_app + endpoints
│       ├── openai_embed.py       # AsyncOpenAI embedder factory
│       ├── faq.py                # FaqIndex with cosine match
│       ├── identity.py           # UIN/DOB verification, per-call attempt budget
│       ├── scheduler.py          # Mock scheduler, one-booking-per-slot
│       ├── escalation.py         # Ticket file writer
│       ├── store.py              # JsonStore atomic writes
│       ├── hashing.py            # SHA-256 caller-number hash
│       └── data/
│           ├── faqs.yaml         # 3 curated FAQ entries
│           └── students.json     # 5 seeded test students
├── tests/                        # pytest tree mirroring src/
│   ├── agent/                    # safety regex/classifier, tools, prompts,
│   │                             # safety-shutdown regression, contract tests
│   ├── backend/                  # store, identity, scheduler, faq, app, escalation
│   └── fixtures/                 # audio + transcripts (populated in Task 21)
├── docs/plans/
│   ├── 2026-04-19-visavoice-design.md              # approved design doc
│   └── 2026-04-19-visavoice-v0-implementation.md   # task-by-task plan
├── .github/workflows/ci.yml      # lint + types + unit tests; contract tests gated on secret
├── pyproject.toml                # uv-managed deps, ruff + pyright config
├── traceability.md               # per-task status, files touched, test results
├── learnings.md                  # gotchas and fix patterns
├── CLAUDE.md                     # project context for Claude Code
└── README.md                     # you are here
```

## Getting started

### Prerequisites

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Install

```bash
git clone https://github.com/ashcastelinocs124/VisaVoice.git
cd VisaVoice
uv sync
```

### Configure

Copy `.env.example` to `.env` and fill in at minimum:

```
OPENAI_API_KEY=sk-...                         # required for embeddings, classifier, Realtime
CALLER_HASH_SALT=generate-with-openssl-rand   # any random 32 bytes
BACKEND_BASE_URL=http://localhost:8080        # default
```

LiveKit and Twilio credentials are only needed for the deploy path; local development + tests run without them.

### Run the backend locally

```bash
uv run python -m visavoice.backend
# → uvicorn on http://0.0.0.0:8080
curl http://localhost:8080/health
# → {"ok":true}
```

Note: startup will fail fast if `OPENAI_API_KEY` is invalid, because the FAQ index tries to build real embeddings during lifespan. Use a real key for local runs, or inject a fake `embed_fn` via `create_app(embed_fn=...)` in your own launcher.

### Run the agent worker locally

Requires valid LiveKit credentials:

```bash
uv run python -m visavoice.agent.main start
```

The worker registers with LiveKit Cloud and waits for inbound call dispatch. Without a live SIP trunk wired to a Twilio DID, no calls will arrive.

## Testing

### Run everything

```bash
uv run pytest tests -v
# → 62 passed
```

Contract tests against the live OpenAI API are **skipped** unless `OPENAI_API_KEY` is set.

### Run just the fast unit suite (same as CI)

```bash
OPENAI_API_KEY=test-no-network \
CALLER_HASH_SALT=local-salt \
  uv run pytest tests -v \
  --ignore=tests/agent/test_tool_contracts.py
# → 62 passed
```

### Lint and type check

```bash
uv run ruff check .
uv run pyright src
```

Both must be clean to pass CI.

### What the tests actually verify

- **`tests/backend/test_store.py`** — atomic-write semantics, including simulated crash between tempfile and rename, and 4-thread concurrent-write corruption test.
- **`tests/backend/test_identity.py`** — attempt budget, leading-zero UINs, `hmac.compare_digest` for timing-safe DoB matching.
- **`tests/backend/test_scheduler.py`** — slot allocation, persistence across instances, no-slots-available handling.
- **`tests/backend/test_app.py`** — full FastAPI endpoint stack with `TestClient`, deterministic `fake_embed` keyed on `md5(text)`.
- **`tests/agent/test_safety_regex.py`** — 17 parametrized cases: 8 HIT examples for each category, 9 adversarial MISS examples (*"i could kill for some coffee"*, *"ice on the roof"*, *"i hit send"*) that a lazy pattern would trip on.
- **`tests/agent/test_safety_shutdown.py`** — regression test that catches the drain/shutdown inversion: asserts `session.drain()` is awaited *and* `ctx.shutdown()` is called without await, using `AsyncMock` vs `MagicMock` to distinguish.
- **`tests/agent/test_tools.py`** — real `httpx.ReadTimeout` injection via `pytest-httpx`, verifies typed error fallback shape.
- **`tests/agent/test_tool_contracts.py`** — real OpenAI API calls at `temperature=0` asserting the model calls the right tool for given conversation states.

## Safety model

Safety is the single highest-stakes part of this system. The contract is:

**Every finalised user transcript runs `safety.scan()` in parallel with the LLM's response generation.** If either the regex layer OR the classifier returns a hit, the in-flight LLM response is cancelled, a hardcoded scripted line is played (referencing the appropriate resource number digit-by-digit, twice), an escalation ticket is written, and the call ends — regardless of what the model would have said next.

### Categories

| Category | Action |
|---|---|
| `self_harm_ideation` | UIUC Counseling Center crisis line + national 988 |
| `acute_medical` | Instruct caller to dial 911 |
| `abuse` | Women's Resources Center + national DV hotline |
| `sevis_termination` | ISSS emergency line or email |
| `ice_contact` | UIUC Police non-emergency + ISSS emergency + rights reminder |
| `police_contact` | 911 or ISSS follow-up line |
| `deportation_threat` | ISSS emergency line |

All scripted lines are in `src/visavoice/agent/safety.py :: SCRIPTS`. **Before piloting with real students, verify all referenced phone numbers are current** — the ones in the code are plausible UIUC numbers but should be re-confirmed with ISSS staff.

### What is *not* trusted

- The LLM's own decision to escalate. It has an `escalate_to_human` tool, but it cannot be the only line of defence.
- The classifier alone. It has a 0.5s timeout; if it fails, the regex is the guarantee.
- ASR perfect transcription. Patterns use common phrasings; the classifier covers the tail.

### Failure-mode policy

- Classifier timeout or exception → treated as non-hit, logged, call continues. **The regex is the non-negotiable layer.**
- Safety handler exception → caught by `add_done_callback`, logged via structlog, does not silently fail (this was the critical bug caught in code review before v0 shipped).
- Regex false positive on an ambiguous input → errs toward escalation. Acceptable.

## Deployment (not yet done)

v0 code is ready to deploy; the telephony wiring isn't. Pending tasks:

1. **Fly.io** — `fly apps create visavoice`, set secrets, `fly deploy`.
2. **Twilio DID** — buy a 217-area number (~$1/mo), set up Elastic SIP trunk origination URI pointing to LiveKit.
3. **LiveKit SIP trunk** — `lk sip inbound-trunk create --numbers "+1217XXXXXXX"` + dispatch rule targeting the `visavoice` agent.
4. **Fixture audio** — record 8 WAV clips for the Tier-3 voice harness (one per scenario).
5. **Tier-3 harness** — implement the Twilio-placed-call + Whisper-transcribe + assert pipeline.
6. **Manual QA** — call the real number, walk through the 8 scenarios.

Full instructions live in `docs/plans/2026-04-19-visavoice-v0-implementation.md` (Milestones 5–7).

## Credentials required (not included in repo)

| Where | Var | Get it from | Cost |
|---|---|---|---|
| Runtime | `OPENAI_API_KEY` | platform.openai.com | ~$0.06–0.24/call-minute |
| Runtime | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | cloud.livekit.io | Free tier for dev |
| Deploy | Twilio account + DID | twilio.com | $1/mo + $0.013/min inbound |
| Deploy | Fly.io account | fly.io | ~$3–5/mo for the container |
| Runtime | `CALLER_HASH_SALT` | `openssl rand -hex 32` | — |
| CI (optional) | `OPENAI_API_KEY` repo secret | GitHub → Settings → Secrets | — |

## Out of scope for v0

- Multilingual (Mandarin, Hindi)
- Real iSTART/Sunapsis appointment integration
- Real human warm transfer (tickets are *written*, not routed)
- SMS or email confirmations
- Authenticated access to SEVIS records or I-20 data
- Multi-worker concurrency
- Consent-recorded retention, DPA with vendors
- Staff dashboard for escalation ticket review
- Callback queue execution
- Load tests, accent-robustness benchmarking, chaos tests

These are captured as "v1 target" in the design doc.

## License

Not yet specified.

## Contributors

- [@ashcastelinocs124](https://github.com/ashcastelinocs124)
- Implementation assisted by Claude Opus 4.7 (1M context) via Claude Code.

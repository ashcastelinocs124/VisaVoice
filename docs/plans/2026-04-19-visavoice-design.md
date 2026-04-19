# visavoice — v0 Design

**Date:** 2026-04-19
**Status:** approved (brainstorming phase)
**Scope:** v0 MVP only. Target architecture is documented separately.

## Summary

A voice-based AI assistant for UIUC International Student & Scholar Services (ISSS). International students dial a phone number and talk to an AI receptionist that answers common questions, books appointments, routes to advisors, and escalates sensitive cases to humans.

**v0 is a single happy-path demo:** one phone number, English only, three curated FAQs, one appointment type, mock booking backend. ~2 weeks of work. Built so that v1 swaps implementations rather than rewriting.

## Product decisions

| Area | v0 decision | Target (v1+) |
|---|---|---|
| Audience | UIUC ISSS with insider access | — |
| Channel | Inbound phone (PSTN) only | same |
| Languages | English only | English + Mandarin + Hindi |
| Identity verification | Spoken UIN + DOB (matches current receptionist practice) | Tiered by risk |
| FAQ knowledge | 3 curated YAML entries | Hybrid: curated for top/sensitive, RAG for long tail |
| Routing | Ask user, safety triggers override | Intent-based tiered routing + safety overrides |
| After-hours | 24/7 available, scope-reduced | same |
| Retention | Metadata + bookings + escalation tickets only; audio/transcripts purge 7d | 30d with redaction + DPA |
| Deploy target | Fly.io, single region (`ord`) | Multi-region, multi-worker |

## Stack

- **Telephony:** Twilio DID → SIP trunk → LiveKit Cloud inbound
- **Orchestration:** LiveKit Agents (Python)
- **Voice model:** OpenAI Realtime (`gpt-realtime`, `alloy` voice), speech-to-speech
- **Safety classifier:** OpenAI `gpt-4.1-mini` (non-blocking parallel call)
- **FAQ embeddings:** OpenAI `text-embedding-3-small`
- **Backend:** FastAPI in the same container, separate process via supervisord
- **Storage:** flat JSON files with atomic writes (`tempfile` + `os.rename`)
- **Hosting:** Fly.io (one machine, one region)

The entire model stack is OpenAI. No Anthropic, no third-party ASR/TTS.

## Architecture

```
Student phone ──► Twilio SIP ──► LiveKit Cloud ──► Agent worker
                                                    │
                                                    ├── OpenAI Realtime (speech-to-speech)
                                                    ├── Safety scanner (regex + gpt-4.1-mini)
                                                    └── Tool calls ──► FastAPI (localhost)
                                                                        ├── /faq/lookup
                                                                        ├── /identity/verify
                                                                        ├── /appointments
                                                                        └── /escalation
```

**Key property:** every state change goes over HTTP to the FastAPI backend. The agent holds no booking state. v1's real iSTART integration is a drop-in swap of `/appointments`, not a refactor.

## Components

### `agent/` — LiveKit worker
- `main.py` — worker entrypoint, session config, tool registration, on-transcript safety hook
- `prompts.py` — system prompt, confirmation scaffolding, tool-use guidance, prompt-injection defenses
- `tools.py` — 4 async tools, thin HTTP wrappers around FastAPI:
  - `lookup_faq(question) → {answer, citation, confidence}` (embedding match, threshold 0.7)
  - `verify_identity(uin, dob) → {verified, student_id?, first_name?}` (max 3 attempts/call)
  - `book_appointment(student_id, appointment_type, preferred_window) → {booking_id, time, advisor}`
  - `escalate_to_human(reason, summary) → {ticket_id}` (writes ticket file; v0 has no real transfer)
- `safety.py` — regex list (~40 patterns) + gpt-4.1-mini classifier; each hit returns `{category, script, severity}`

### `backend/` — FastAPI
- `app.py` — 4 endpoints matching the tool set
- `data/faqs.yaml` — 3 entries: OPT basics, travel signature on I-20, address-change reporting
- `data/students.json` — 5 seeded test students (one name with diacritic, one UIN starting with 0)
- `data/appointments.json` — initially empty, atomic writes
- `data/escalations/` — per-ticket JSON files
- `data/calls/` — per-call record files (metadata only; no audio, no full transcript)

### `Dockerfile`, `fly.toml`, `supervisord.conf`, `.env.example`

## Data flow (happy-path booking)

1. PSTN call → Twilio → LiveKit → agent worker → Realtime session attached
2. Boot-cached TTS greeting (not generated)
3. Student states intent → model decides `verify_identity` must run first
4. Agent asks for UIN + DOB; **reads back for explicit confirmation** before calling the tool
5. `verify_identity` → HTTP → FastAPI → constant-time compare → returns `{verified: true, ...}`
6. Agent asks for preferred time window
7. `book_appointment` → HTTP → FastAPI → picks next open slot, atomic write, returns booking
8. Agent confirms booking specifics to caller, ends call
9. Post-call hook writes call record (metadata only), schedules purge

Concurrent throughout: `user_speech_committed` fires on every final transcript → `safety.scan()` runs in parallel with the model's response. Regex layer is sub-ms; classifier layer is 80–200ms. A hit short-circuits the turn via `session.interrupt()` + scripted line + `escalate_to_human` + `session.end()`.

## Error handling

| Failure class | Behavior |
|---|---|
| ASR mishears UIN/DOB | Required read-back confirmation before `verify_identity` |
| 3 failed verifications | Scripted line + escalation ticket + end call |
| Tool timeout (3s) | One retry; scripted recovery line |
| Tool typed error | Model handles conversationally per prompt guidance |
| Realtime transient disconnect | LiveKit auto-reconnects; scripted hold line if >3s |
| Realtime hard failure | Scripted tech-trouble line + tech_failure ticket + end |
| Twilio/LiveKit failure at answer | Twilio static-audio TwiML fallback (no code) |
| Safety classifier timeout | Treat as non-hit, log WARN, continue (regex is the guarantee) |
| Safety handler exception | Catch, log ERROR, continue — never block happy path |
| Backend crash | Tool returns `{error: "backend_down"}` → scripted callback flow, standalone ticket writer |
| Prompt injection | System-prompt rejection clause + tools are only state-change path |
| Rate limit hit | Scripted line + end call |
| Non-English caller | Scripted English-only line + callback ticket |

Explicitly **not** handled in v0: partial bookings, concurrent booking conflicts (single-worker), multi-language input.

## Safety scanner — detailed behavior

The on-transcript hook is the single most important piece of this design. It runs *in parallel* with the model, not before it, so the happy path pays zero latency cost.

**Mechanism:**
1. LiveKit's `user_speech_committed` event fires when VAD closes a turn and ASR finalizes.
2. Handler calls `safety.scan(transcript)`:
   - Regex pass (sub-ms) over ~40 high-precision patterns: self-harm, SEVIS termination, deportation threats, ICE, abuse, acute medical.
   - On regex miss, `gpt-4.1-mini` classifier over last 3 turns (80–200ms).
3. On hit (either layer):
   - `session.interrupt()` cancels the in-flight Realtime response.
   - `session.say(SCRIPTS[category], allow_interruptions=False)` plays a **hardcoded, pre-rendered** scripted line (not generated). The script reads the relevant referral number digit-by-digit twice.
   - `tools.escalate_to_human(reason, summary)` writes a high-severity ticket.
   - `session.end()`.

**Defense in depth:** the model also has its own `escalate_to_human` tool. Redundant is good. The hook is the guarantee — even if the model is chatting past a distress signal, the hook fires and ends the call.

**Failure mode policy:** the scanner must never block the happy path. Timeouts or exceptions are logged and skipped; regex is the non-negotiable layer.

## Testing

Four tiers, each catching different failure modes.

**Tier 1 — Unit (pytest, offline, <2 min on CI)**
- Every backend endpoint, happy + typed errors + atomic-write concurrency
- `safety.py` table-driven: ~60 labeled utterances (regex offline, classifier mocked) — *the most important test file*
- ~20 prompt-injection utterances against mocked model

**Tier 2 — Tool-call contract tests**
- Text-only transcript + tool schema → real OpenAI chat completions (Realtime-equivalent tool format) at `temperature=0` → assert correct tool name + arg shape
- ~15 scenarios, runs on CI

**Tier 3 — Scripted end-to-end voice tests**
- Harness places real PSTN call into deployed number; plays pre-recorded WAVs; records the call
- Post-call: Whisper transcribe + structural asserts (booking written, duration bounds, escalation fired-or-not, confirmation line contains booked time)
- 8 scenarios: happy-path, UIN miscorrection, 3-failed-verifications, FAQ-hit, FAQ-miss, self-harm trigger, prompt injection, non-English caller
- Manual before each deploy in v0; nightly in v1

**Tier 4 — Manual QA**
- Human runs the 8 scenarios. Captures barge-in feel, latency, TTS pronunciation of names/numbers, overall "does it sound like ISSS"
- Required before pilot. Required after any prompt change.

**CI pipeline (GitHub Actions):**
- PR: tier 1 + 2
- Merge to main: same + deploy to Fly.io staging
- Deploy tag: tier 3 runs against staging, must pass before promoting to prod

**Fixtures:**
- `tests/fixtures/audio/` — ~20 pre-recorded WAVs (checked in)
- `tests/fixtures/transcripts/` — golden transcripts
- `tests/fixtures/students.json` — 5 edge-case students

**Explicitly out of scope for v0 testing:** load tests (single concurrent call only), accent robustness (punted with English-only), chaos tests on Twilio/LiveKit outages.

## Open questions deferred to v1

- iSTART/Sunapsis integration contract (real appointment system)
- Mandarin + Hindi content, TTS voice selection, ASR tuning
- Real warm-transfer mechanism (SIP refer / Twilio dial verb)
- Consent language + DPA with OpenAI/LiveKit/Twilio for 30-day retention
- Staff dashboard for escalation ticket review
- Callback queue execution
- Analytics / intent taxonomy

## Non-goals for v0

- Multilingual support
- Real appointment system integration
- Real human transfer (tickets are written, not routed)
- SMS or email (only scripted references to email addresses)
- Authenticated access to SEVIS records or I-20 data
- Multi-worker concurrency

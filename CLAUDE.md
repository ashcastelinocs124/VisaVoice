# visavoice — CLAUDE.md

> Status: v0 code-only milestones implemented on `feat/v0`. Tasks 18–23 (Fly.io deploy, Twilio/LiveKit SIP wiring, Tier-3 voice harness) still require account/infra access and are deferred.

## Project summary
Voice-based AI assistant for international students to book/reschedule/cancel ISSS (International Student & Scholar Services) appointments, answer common questions, route to the correct advisor, and escalate sensitive cases to humans.

## Completed Work

### v0 code — 2026-04-19
- Inbound phone AI receptionist (English only) — design at `docs/plans/2026-04-19-visavoice-design.md`, plan at `docs/plans/2026-04-19-visavoice-v0-implementation.md`, traceability at `traceability.md`
- Stack: Twilio (to be wired) → LiveKit Agents 1.5.4 → OpenAI Realtime (`gpt-realtime`, voice=alloy) with OpenAI `gpt-4.1-mini` safety classifier and `text-embedding-3-small` for FAQ retrieval
- Backend: FastAPI with atomic-write JSON stores. Endpoints: `/health`, `/faq/lookup`, `/identity/verify`, `/appointments`, `/escalation`
- Agent: four registered tools (`lookup_faq`, `verify_identity`, `book_appointment`, `escalate_to_human`) + parallel safety scanner on every final user transcript (regex + classifier; regex is the non-negotiable layer)
- Tests: 62 unit/integration tests green; ruff clean; pyright 0 errors. CI workflow at `.github/workflows/ci.yml`
- Key conventions introduced: src-layout package with `[build-system] = hatchling`, FastAPI lifespan (not deprecated startup event), safety-hit shutdown path extracted to module-level `handle_safety_scan` for testability

## Git push policy (HARD RULE)

Every push to a remote MUST go through the `/gitpush` skill. Never run `git push`, `gh repo create --push`, or any other push-equivalent directly in Bash — even for "simple" pushes to an already-tracked branch. The skill runs a pre-push secret scan (env files, `.pem`/`.key` files, credentials in diff hunks) that raw `git push` skips. If a push happens outside the skill, log it in `learnings.md` and run `/gitpush` retroactively against the pushed branch as an audit.

## Learnings
This project maintains a `learnings.md` file at the project root. Add entries whenever you discover something interesting. Each entry must include a **Ref** subtitle pointing to the relevant CLAUDE.md section. Only read `learnings.md` when its contents are directly relevant to the current task.

Use the `/capture-learnings` skill at the end of sessions to do this automatically.

## Memory System

### Short-term memory (`short_term_memory.md`)
Holds a detailed log of the past 5 immediate tasks — what was done, why, and the outcome. When a new task is completed, append it. If there are more than 5 entries, summarize the oldest into `long_term_memory.md` before removing it.

### Long-term memory (`long_term_memory.md`)
When a task ages out of short-term memory, write a condensed summary (2–3 lines) here.

**Pruning rule:** Every 10 sessions, review `long_term_memory.md` against `CLAUDE.md`. Delete any entries no longer relevant.

### Loading priority
At the start of every session, read both files into context:
1. `short_term_memory.md` first — most important.
2. `long_term_memory.md` second — background context.

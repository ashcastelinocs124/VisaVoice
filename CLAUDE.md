# visavoice — CLAUDE.md

> Status: brainstorming. Tech stack and architecture TBD pending design approval.

## Project summary
Voice-based AI assistant for international students to book/reschedule/cancel ISSS (International Student & Scholar Services) appointments, answer common questions, route to the correct advisor, and escalate sensitive cases to humans.

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

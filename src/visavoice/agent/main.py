"""
LiveKit Agent worker for visavoice v0.

Wires together:
- OpenAI Realtime speech-to-speech (gpt-realtime, voice=alloy)
- HTTP tool client to the FastAPI backend (ToolClient)
- Parallel safety scanner on every finalized user transcript (Scanner)
- System prompt from visavoice.agent.prompts.SYSTEM_PROMPT

Adapted for livekit-agents 1.5.4. See the deviations list in
traceability.md (Task 17) for the mapping from the 0.12.x blueprint.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import uuid
from pathlib import Path

import structlog
from livekit.agents import (
    Agent,
    AgentSession,
    ConversationItemAddedEvent,
    JobContext,
    UserInputTranscribedEvent,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import openai as lk_openai
from livekit.plugins import silero

from ..config import Settings
from .prompts import SYSTEM_PROMPT
from .safety import Scanner, make_openai_classifier
from .tools import ToolClient

log = structlog.get_logger()


def _hash_caller(number: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}|{number}".encode()).hexdigest()


async def handle_safety_scan(
    *,
    transcript: str,
    session: AgentSession,
    ctx: JobContext,
    scanner: Scanner,
    tools: ToolClient,
    last_turns: list[dict],
    call_id: str,
) -> None:
    """Run the safety scanner; on hit, interrupt, speak script, escalate, shut down.

    Extracted to module-level so it can be unit-tested with mocked dependencies.
    Drain/shutdown semantics (livekit-agents 1.5.4):
    - ``AgentSession.drain`` is async — must be awaited.
    - ``JobContext.shutdown`` is sync (returns ``None``) — must NOT be awaited.
    """
    result = await scanner.scan(transcript)
    if not result.hit:
        return
    log.warning(
        "safety_hit",
        call_id=call_id,
        category=result.category,
        layer=result.layer,
        severity=result.severity,
    )
    with contextlib.suppress(Exception):
        # interrupt() returns an asyncio.Future in 1.x — awaiting is fine.
        await session.interrupt()
    if result.script:
        await session.say(result.script, allow_interruptions=False)
    await tools.escalate_to_human(
        category=result.category or "unknown",
        severity=result.severity or "high",
        summary=f"Safety trigger: {result.category} via {result.layer}.",
        last_turns=last_turns[-5:],
        trigger_layer=result.layer or "unknown",
    )
    # drain() is async in 1.x — must be awaited so pending turns flush before shutdown.
    await session.drain()
    # shutdown() is sync in 1.x — returns None, must NOT be awaited.
    ctx.shutdown()


async def entrypoint(ctx: JobContext) -> None:
    """LiveKit worker entrypoint. Invoked once per job (per call)."""
    settings = Settings()
    await ctx.connect()

    # Best-effort caller number extraction (SIP participant attribute).
    caller_number = ""
    for p in ctx.room.remote_participants.values():
        caller_number = p.attributes.get("sip.phoneNumber", "") or caller_number
    call_id = f"call_{uuid.uuid4().hex[:10]}"
    caller_hash = _hash_caller(caller_number, settings.caller_hash_salt)

    tools = ToolClient(
        base_url=settings.backend_base_url,
        call_id=call_id,
        caller_hash=caller_hash,
    )
    scanner = Scanner(classifier=make_openai_classifier(settings.openai_api_key))

    # Rolling transcript buffer used for escalation payloads.
    last_turns: list[dict] = []

    @function_tool()
    async def lookup_faq(question: str) -> str:
        """Look up an answer to a common ISSS question."""
        r = await tools.lookup_faq(question=question)
        return json.dumps(r)

    @function_tool()
    async def verify_identity(uin: str, dob: str) -> str:
        """Verify the caller's identity using UIN and date of birth (YYYY-MM-DD).

        Only call after reading back and getting confirmation from the caller.
        """
        r = await tools.verify_identity(uin=uin, dob=dob)
        return json.dumps(r)

    @function_tool()
    async def book_appointment(
        student_id: str, appointment_type: str, preferred_window: str
    ) -> str:
        """Book an appointment.

        preferred_window values: monday_morning, monday_afternoon, ...,
        friday_morning, friday_afternoon.
        """
        r = await tools.book_appointment(
            student_id=student_id,
            appointment_type=appointment_type,
            preferred_window=preferred_window,
        )
        return json.dumps(r)

    @function_tool()
    async def escalate_to_human(reason: str, summary: str) -> str:
        """Create an escalation ticket for human follow-up."""
        r = await tools.escalate_to_human(
            category=reason,
            severity="medium",
            summary=summary,
            last_turns=last_turns[-5:],
            trigger_layer="model",
        )
        return json.dumps(r)

    session = AgentSession(
        llm=lk_openai.realtime.RealtimeModel(
            model="gpt-realtime",
            voice="alloy",
            temperature=0.6,
        ),
        vad=silero.VAD.load(),
    )

    agent = Agent(
        instructions=SYSTEM_PROMPT,
        tools=[lookup_faq, verify_identity, book_appointment, escalate_to_human],
    )

    def _log_safety_task_exception(task: asyncio.Task) -> None:
        """Done-callback: surface exceptions raised inside the fire-and-forget
        safety-scan task. Without this, `asyncio.create_task` only logs errors at
        GC time, which is fail-open behavior and hides real bugs.
        """
        exc = task.exception()
        if exc is not None:
            log.error("safety_handler_failed", exc_info=exc, call_id=call_id)

    # --- Event wiring ---------------------------------------------------------
    # 1.x renamed the finalized-user-transcript event:
    #   0.12.x: "user_speech_committed" (AlternativeTranscript wrapper)
    #   1.x:    "user_input_transcribed" (UserInputTranscribedEvent with
    #           .transcript:str and .is_final:bool)
    # We filter to is_final=True so the safety hook only fires on committed turns.
    @session.on("user_input_transcribed")
    def _on_user_input(event: UserInputTranscribedEvent) -> None:
        if not event.is_final:
            return
        text = event.transcript or ""
        last_turns.append({"role": "user", "text": text})
        # Fire-and-forget so the safety hook runs in parallel with the model.
        safety_task = asyncio.create_task(
            handle_safety_scan(
                transcript=text,
                session=session,
                ctx=ctx,
                scanner=scanner,
                tools=tools,
                last_turns=last_turns,
                call_id=call_id,
            )
        )
        safety_task.add_done_callback(_log_safety_task_exception)

    # 1.x emits assistant turns via "conversation_item_added" whose .item is a
    # ChatMessage with .role and .text_content. This replaces 0.12.x's
    # "agent_speech_committed" hook.
    @session.on("conversation_item_added")
    def _on_conversation_item(event: ConversationItemAddedEvent) -> None:
        item = event.item
        role = getattr(item, "role", None)
        if role != "assistant":
            return
        text = getattr(item, "text_content", None) or ""
        if text:
            last_turns.append({"role": "assistant", "text": text})

    # --- Shutdown hook --------------------------------------------------------
    async def _on_shutdown() -> None:
        record = {
            "call_id": call_id,
            "caller_hash": caller_hash,
            "turns": len(last_turns),
        }
        calls_dir = Path("backend_data/calls")
        calls_dir.mkdir(parents=True, exist_ok=True)
        (calls_dir / f"{call_id}.json").write_text(json.dumps(record, indent=2))
        await tools.close()

    # 1.x: add_shutdown_callback is a method, not a decorator. Call directly.
    ctx.add_shutdown_callback(_on_shutdown)

    await session.start(agent=agent, room=ctx.room)
    await session.say("Thanks for calling UIUC ISSS. How can I help?", allow_interruptions=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    main()

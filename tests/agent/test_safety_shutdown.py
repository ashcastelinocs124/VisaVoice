"""Regression tests for the safety-scan shutdown path.

Guards against the drain/shutdown inversion bug caught in code review: in
livekit-agents 1.5.4, ``AgentSession.drain`` is async (must be awaited) while
``JobContext.shutdown`` is sync (must NOT be awaited). An earlier version of
``handle_safety_scan`` had these inverted, suppressed by two ``# type: ignore``
comments, which produced a never-scheduled coroutine for drain and a
``TypeError: object NoneType can't be used in 'await' expression`` for shutdown.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from visavoice.agent.main import handle_safety_scan


async def test_safety_hit_drains_and_shuts_down():
    """On a safety hit: drain is awaited, shutdown is called (sync), say+escalate happen."""
    session = MagicMock()
    session.drain = AsyncMock()
    session.interrupt = AsyncMock()
    session.say = AsyncMock()

    ctx = MagicMock()
    ctx.shutdown = MagicMock(return_value=None)

    scanner = MagicMock()
    scanner.scan = AsyncMock(
        return_value=MagicMock(
            hit=True,
            category="self_harm_ideation",
            severity="high",
            script="hardcoded script",
            layer="regex",
        )
    )

    tools = MagicMock()
    tools.escalate_to_human = AsyncMock(return_value={"ticket_id": "esc_x"})

    await handle_safety_scan(
        transcript="i can't live like this",
        session=session,
        ctx=ctx,
        scanner=scanner,
        tools=tools,
        last_turns=[],
        call_id="c1",
    )

    # drain is async — must be awaited exactly once
    session.drain.assert_awaited_once()
    assert session.drain.await_count == 1

    # shutdown is sync — must be called exactly once with no args, and must NOT be awaited
    ctx.shutdown.assert_called_once_with()

    # The script must have been spoken and an escalation ticket created
    session.say.assert_awaited_once()
    tools.escalate_to_human.assert_awaited_once()


async def test_safety_miss_is_noop():
    """On a safety miss: no drain, no shutdown, no say, no escalation."""
    session = MagicMock()
    session.drain = AsyncMock()
    session.interrupt = AsyncMock()
    session.say = AsyncMock()

    ctx = MagicMock()
    ctx.shutdown = MagicMock(return_value=None)

    scanner = MagicMock()
    scanner.scan = AsyncMock(return_value=MagicMock(hit=False))

    tools = MagicMock()
    tools.escalate_to_human = AsyncMock()

    await handle_safety_scan(
        transcript="what are library hours?",
        session=session,
        ctx=ctx,
        scanner=scanner,
        tools=tools,
        last_turns=[],
        call_id="c1",
    )

    session.drain.assert_not_awaited()
    ctx.shutdown.assert_not_called()
    session.say.assert_not_awaited()
    tools.escalate_to_human.assert_not_awaited()


async def test_safety_hit_without_script_still_shuts_down():
    """Even if no hardcoded script is set for the category, we still drain+shutdown."""
    session = MagicMock()
    session.drain = AsyncMock()
    session.interrupt = AsyncMock()
    session.say = AsyncMock()

    ctx = MagicMock()
    ctx.shutdown = MagicMock(return_value=None)

    scanner = MagicMock()
    scanner.scan = AsyncMock(
        return_value=MagicMock(
            hit=True,
            category="other",
            severity="medium",
            script=None,
            layer="classifier",
        )
    )

    tools = MagicMock()
    tools.escalate_to_human = AsyncMock(return_value={"ticket_id": "esc_y"})

    await handle_safety_scan(
        transcript="arbitrary",
        session=session,
        ctx=ctx,
        scanner=scanner,
        tools=tools,
        last_turns=[],
        call_id="c2",
    )

    session.say.assert_not_awaited()  # no script → no say
    tools.escalate_to_human.assert_awaited_once()
    session.drain.assert_awaited_once()
    ctx.shutdown.assert_called_once_with()

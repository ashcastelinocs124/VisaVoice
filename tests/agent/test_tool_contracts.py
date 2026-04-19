import os
import json
import pytest
from openai import AsyncOpenAI


pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="requires OPENAI_API_KEY",
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_faq",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_identity",
            "parameters": {
                "type": "object",
                "properties": {"uin": {"type": "string"}, "dob": {"type": "string"}},
                "required": ["uin", "dob"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {"type": "string"},
                    "appointment_type": {"type": "string"},
                    "preferred_window": {"type": "string"},
                },
                "required": ["student_id", "appointment_type", "preferred_window"],
            },
        },
    },
]


async def _run(messages):
    client = AsyncOpenAI()
    resp = await client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0,
    )
    return resp.choices[0].message


SYS = "You are the ISSS voice assistant. Use tools when appropriate."


async def test_faq_intent_calls_lookup_faq():
    msg = await _run([
        {"role": "system", "content": SYS},
        {"role": "user", "content": "when can i apply for OPT?"},
    ])
    assert msg.tool_calls
    assert msg.tool_calls[0].function.name == "lookup_faq"


async def test_booking_intent_after_verification_calls_book():
    msg = await _run([
        {"role": "system", "content": SYS + " The user is verified as student s_042."},
        {"role": "user", "content": "book me a general advising appointment for thursday afternoon"},
    ])
    assert msg.tool_calls
    assert msg.tool_calls[0].function.name == "book_appointment"
    args = json.loads(msg.tool_calls[0].function.arguments)
    assert args["preferred_window"] == "thursday_afternoon"
    assert args["appointment_type"] == "general_advising"


async def test_unauthenticated_user_requests_booking_triggers_verify_first():
    msg = await _run([
        {"role": "system", "content": SYS + " The user is NOT verified. You must verify identity before booking."},
        {"role": "user", "content": "my UIN is 654321098 and DOB is March 14th 2002, book me an appointment"},
    ])
    assert msg.tool_calls
    assert msg.tool_calls[0].function.name == "verify_identity"

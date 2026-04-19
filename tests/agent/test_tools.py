import pytest
from visavoice.agent.tools import ToolClient


@pytest.fixture
def client():
    return ToolClient(base_url="http://backend:8080", call_id="c1", caller_hash="h")


async def test_verify_identity(httpx_mock, client):
    httpx_mock.add_response(
        url="http://backend:8080/identity/verify",
        json={"verified": True, "student_id": "s_042", "first_name": "Mei", "reason": None},
    )
    r = await client.verify_identity(uin="654321098", dob="2002-03-14")
    assert r["verified"] is True


async def test_lookup_faq(httpx_mock, client):
    httpx_mock.add_response(
        url="http://backend:8080/faq/lookup",
        json={"match": True, "confidence": 0.9, "entry": {"id": "opt_basics", "question": "q", "answer": "a", "citation_url": "u"}},
    )
    r = await client.lookup_faq(question="When can I apply for OPT?")
    assert r["match"] is True


async def test_book_appointment(httpx_mock, client):
    httpx_mock.add_response(
        url="http://backend:8080/appointments",
        json={"booked": True, "booking_id": "apt_1", "slot_iso": "2026-04-23T14:00+00:00", "advisor": "Advisor Chen", "reason": None},
    )
    r = await client.book_appointment(
        student_id="s_042", appointment_type="general_advising",
        preferred_window="thursday_afternoon",
    )
    assert r["booked"] is True
    assert r["advisor"] == "Advisor Chen"


async def test_escalate(httpx_mock, client):
    httpx_mock.add_response(
        url="http://backend:8080/escalation", json={"ticket_id": "esc_abc"},
    )
    r = await client.escalate_to_human(
        category="advisor_request", severity="medium", summary="", last_turns=[], trigger_layer="model",
    )
    assert r["ticket_id"] == "esc_abc"


async def test_timeout_becomes_typed_error(httpx_mock, client):
    import httpx
    httpx_mock.add_exception(httpx.ReadTimeout("timeout"))
    r = await client.verify_identity(uin="x", dob="y")
    assert r == {"verified": False, "reason": "timeout"}

import json

from visavoice.backend.escalation import EscalationService


def test_writes_ticket_file(tmp_path):
    svc = EscalationService(dir=tmp_path)
    ticket = svc.create(
        call_id="c1", caller_hash="abc", category="self_harm_ideation",
        severity="high", summary="…", last_turns=[], trigger_layer="regex",
    )
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["ticket_id"] == ticket.ticket_id
    assert data["category"] == "self_harm_ideation"
    assert data["severity"] == "high"
    assert data["staff_review_required"] is True


def test_multiple_tickets(tmp_path):
    svc = EscalationService(dir=tmp_path)
    for i in range(3):
        svc.create(call_id=f"c{i}", caller_hash="h", category="advisor_request",
                   severity="medium", summary="", last_turns=[], trigger_layer="model")
    assert len(list(tmp_path.glob("*.json"))) == 3

import pytest
from fastapi.testclient import TestClient
from visavoice.backend.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    import hashlib

    async def fake_embed(texts):
        # Deterministic per-text bucketing: same text -> same vector, different text
        # almost always -> orthogonal vector. Deviation from spec (which used `i % 8`);
        # the spec's index-based bucketing collapsed single-item build and lookup calls
        # to the same vector and made `test_faq_lookup_miss` impossible to satisfy.
        # Uses md5 (not Python's hash()) for stability across processes.
        vecs = []
        for t in texts:
            v = [0.0] * 8
            bucket = int.from_bytes(hashlib.md5(t.encode()).digest()[:4], "big") % 8
            v[bucket] = 1.0
            vecs.append(v)
        return vecs

    app = create_app(
        data_dir=tmp_path,
        seed_students=[{
            "student_id": "s_042", "uin": "654321098", "dob": "2002-03-14",
            "first_name": "Mei", "last_name": "Chen", "email": "mei@illinois.edu",
        }],
        seed_faqs=[{"id": "opt_basics", "question": "When can I apply for OPT?",
                    "answer": "OPT…", "citation_url": "u"}],
        embed_fn=fake_embed,
    )
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_identity_verify_success(client):
    r = client.post("/identity/verify", json={"call_id": "c1", "uin": "654321098", "dob": "2002-03-14"})
    assert r.status_code == 200
    assert r.json() == {"verified": True, "student_id": "s_042", "first_name": "Mei", "reason": None}


def test_identity_verify_mismatch(client):
    r = client.post("/identity/verify", json={"call_id": "c1", "uin": "654321098", "dob": "1999-01-01"})
    assert r.json()["verified"] is False
    assert r.json()["reason"] == "mismatch"


def test_faq_lookup_hit(client):
    r = client.post("/faq/lookup", json={"question": "When can I apply for OPT?"})
    data = r.json()
    assert data["match"] is True
    assert data["entry"]["id"] == "opt_basics"


def test_faq_lookup_miss(client):
    r = client.post("/faq/lookup", json={"question": "wholly unrelated chaos"})
    assert r.json()["match"] is False


def test_book_appointment(client):
    r = client.post("/appointments", json={
        "student_id": "s_042", "appointment_type": "general_advising",
        "preferred_window": "thursday_afternoon",
    })
    data = r.json()
    assert data["booked"] is True
    assert data["advisor"].startswith("Advisor")


def test_escalation(client):
    r = client.post("/escalation", json={
        "call_id": "c1", "caller_hash": "abc", "category": "advisor_request",
        "severity": "medium", "summary": "s", "last_turns": [], "trigger_layer": "model",
    })
    assert r.status_code == 200
    assert "ticket_id" in r.json()

import pytest
from visavoice.backend.identity import IdentityService, VerifyResult


STUDENTS = [
    {"student_id": "s_042", "uin": "654321098", "dob": "2002-03-14", "first_name": "Mei", "last_name": "Chen", "email": "mei@illinois.edu"},
    {"student_id": "s_099", "uin": "012345678", "dob": "2000-12-31", "first_name": "Zara", "last_name": "Ahmed", "email": "zara@illinois.edu"},
]

def make():
    return IdentityService(students=STUDENTS, max_attempts_per_call=3)


def test_verified():
    svc = make()
    r = svc.verify(call_id="c1", uin="654321098", dob="2002-03-14")
    assert r == VerifyResult(verified=True, student_id="s_042", first_name="Mei", reason=None)


def test_wrong_dob_not_verified():
    svc = make()
    r = svc.verify(call_id="c1", uin="654321098", dob="1999-01-01")
    assert r.verified is False
    assert r.reason == "mismatch"


def test_unknown_uin():
    svc = make()
    r = svc.verify(call_id="c1", uin="000000000", dob="2000-01-01")
    assert r.verified is False
    assert r.reason == "not_found"


def test_leading_zero_uin():
    svc = make()
    r = svc.verify(call_id="c1", uin="012345678", dob="2000-12-31")
    assert r.verified is True


def test_max_attempts_enforced_per_call():
    svc = make()
    for _ in range(3):
        svc.verify(call_id="c1", uin="000", dob="2000-01-01")
    r = svc.verify(call_id="c1", uin="654321098", dob="2002-03-14")
    assert r.verified is False
    assert r.reason == "too_many_attempts"

    fresh = svc.verify(call_id="c2", uin="654321098", dob="2002-03-14")
    assert fresh.verified is True

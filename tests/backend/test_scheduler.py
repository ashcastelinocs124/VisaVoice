from datetime import UTC, datetime

from visavoice.backend.scheduler import BookResult, Scheduler


def fixed_now():
    return datetime(2026, 4, 19, 18, 0, tzinfo=UTC)


def test_books_next_available_in_window(tmp_path):
    sched = Scheduler(path=tmp_path / "appts.json", now_fn=fixed_now)
    r = sched.book(student_id="s_042", appointment_type="general_advising",
                   preferred_window="thursday_afternoon")
    assert isinstance(r, BookResult)
    assert r.booked is True
    assert r.slot_iso.startswith("2026-04-23T")
    assert "Advisor" in r.advisor


def test_persists_across_instances(tmp_path):
    s1 = Scheduler(path=tmp_path / "a.json", now_fn=fixed_now)
    r1 = s1.book(student_id="s_042", appointment_type="general_advising",
                 preferred_window="thursday_afternoon")
    s2 = Scheduler(path=tmp_path / "a.json", now_fn=fixed_now)
    r2 = s2.book(student_id="s_042", appointment_type="general_advising",
                 preferred_window="thursday_afternoon")
    assert r1.slot_iso != r2.slot_iso


def test_no_slots_returns_no_match(tmp_path):
    sched = Scheduler(path=tmp_path / "a.json", now_fn=fixed_now)
    results = [sched.book("s_042", "general_advising", "thursday_afternoon") for _ in range(10)]
    assert any(r.booked is False and r.reason == "no_slots_available" for r in results)


def test_invalid_window(tmp_path):
    sched = Scheduler(path=tmp_path / "a.json", now_fn=fixed_now)
    r = sched.book("s_042", "general_advising", "midnight_madness")
    assert r.booked is False
    assert r.reason == "invalid_window"

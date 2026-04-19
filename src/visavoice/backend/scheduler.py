import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from .store import JsonStore

ADVISORS = ["Advisor Chen", "Advisor Patel", "Advisor Kim"]
SLOT_TIMES_BY_WINDOW = {
    "monday_morning":     (0, [time(9), time(10), time(11)]),
    "monday_afternoon":   (0, [time(13), time(14), time(15)]),
    "tuesday_morning":    (1, [time(9), time(10), time(11)]),
    "tuesday_afternoon":  (1, [time(13), time(14), time(15)]),
    "wednesday_morning":  (2, [time(9), time(10), time(11)]),
    "wednesday_afternoon":(2, [time(13), time(14), time(15)]),
    "thursday_morning":   (3, [time(9), time(10), time(11)]),
    "thursday_afternoon": (3, [time(13), time(14), time(15)]),
    "friday_morning":     (4, [time(9), time(10), time(11)]),
    "friday_afternoon":   (4, [time(13), time(14), time(15)]),
}


@dataclass(frozen=True)
class BookResult:
    booked: bool
    booking_id: str | None = None
    slot_iso: str | None = None
    advisor: str | None = None
    reason: str | None = None


class Scheduler:
    def __init__(self, path: Path, now_fn: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self._store = JsonStore(path, default=[])
        self._now = now_fn

    def book(self, student_id: str, appointment_type: str, preferred_window: str) -> BookResult:
        if preferred_window not in SLOT_TIMES_BY_WINDOW:
            return BookResult(booked=False, reason="invalid_window")

        weekday, slot_times = SLOT_TIMES_BY_WINDOW[preferred_window]
        now = self._now()

        for week_offset in range(3):
            target_date = _next_weekday(now, weekday, week_offset)
            for t in slot_times:
                slot_dt = datetime.combine(target_date.date(), t, tzinfo=UTC)
                if slot_dt <= now:
                    continue
                advisor = self._first_free_advisor(slot_dt)
                if advisor is None:
                    continue
                booking = {
                    "booking_id": f"apt_{uuid.uuid4().hex[:8]}",
                    "student_id": student_id,
                    "appointment_type": appointment_type,
                    "slot_iso": slot_dt.isoformat(),
                    "advisor": advisor,
                    "created_at": now.isoformat(),
                }
                existing = self._store.read()
                existing.append(booking)
                self._store.write(existing)
                return BookResult(booked=True, booking_id=booking["booking_id"],
                                  slot_iso=booking["slot_iso"], advisor=advisor)
        return BookResult(booked=False, reason="no_slots_available")

    def _first_free_advisor(self, slot_dt: datetime) -> str | None:
        """Return first advisor with no booking at this slot, or None if slot is fully taken."""
        existing = self._store.read()
        taken = {b["advisor"] for b in existing if b["slot_iso"] == slot_dt.isoformat()}
        # One booking per slot regardless of advisor — once any advisor books, slot is taken.
        if taken:
            return None
        return ADVISORS[0]


def _next_weekday(now: datetime, weekday: int, week_offset: int) -> datetime:
    days_ahead = (weekday - now.weekday()) % 7
    if days_ahead == 0 and now.hour >= 17:
        days_ahead = 7
    return now + timedelta(days=days_ahead + 7 * week_offset)

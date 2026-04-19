import hmac
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class VerifyResult:
    verified: bool
    student_id: str | None = None
    first_name: str | None = None
    reason: str | None = None


class IdentityService:
    def __init__(self, students: list[dict], max_attempts_per_call: int = 3):
        self._by_uin = {s["uin"]: s for s in students}
        self._max = max_attempts_per_call
        self._attempts: dict[str, int] = defaultdict(int)

    def verify(self, call_id: str, uin: str, dob: str) -> VerifyResult:
        if self._attempts[call_id] >= self._max:
            return VerifyResult(verified=False, reason="too_many_attempts")
        self._attempts[call_id] += 1

        student = self._by_uin.get(uin)
        if student is None:
            return VerifyResult(verified=False, reason="not_found")

        if not hmac.compare_digest(student["dob"], dob):
            return VerifyResult(verified=False, reason="mismatch")

        return VerifyResult(
            verified=True,
            student_id=student["student_id"],
            first_name=student["first_name"],
        )

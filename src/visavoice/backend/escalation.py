import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# Must stay in sync with visavoice.agent.safety.HIGH_SEVERITY.
# The agent-side scanner is the authoring source, but the backend re-declares the set
# rather than importing across the agent/backend boundary so the two packages remain
# independently deployable. If you add a category here, mirror it in agent/safety.py.
HIGH_SEVERITY_CATEGORIES = {
    "self_harm_ideation",
    "acute_medical",
    "abuse",
    "deportation_threat",
    "ice_contact",
}


@dataclass(frozen=True)
class EscalationTicket:
    ticket_id: str
    path: Path


class EscalationService:
    def __init__(self, dir: Path):
        self._dir = Path(dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def create(self, *, call_id: str, caller_hash: str, category: str,
               severity: str, summary: str, last_turns: list[dict],
               trigger_layer: str) -> EscalationTicket:
        ts = datetime.now(UTC).isoformat()
        ticket_id = f"esc_{uuid.uuid4().hex[:10]}"
        path = self._dir / f"{ts.replace(':', '').replace('-', '')}_{ticket_id}.json"
        payload = {
            "ticket_id": ticket_id,
            "timestamp": ts,
            "call_id": call_id,
            "caller_hash": caller_hash,
            "category": category,
            "severity": severity,
            "trigger_layer": trigger_layer,
            "summary": summary,
            "last_turns": last_turns,
            "staff_review_required": severity == "high" or category in HIGH_SEVERITY_CATEGORIES,
        }
        path.write_text(json.dumps(payload, indent=2))
        return EscalationTicket(ticket_id=ticket_id, path=path)

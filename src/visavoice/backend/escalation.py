import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


HIGH_SEVERITY_CATEGORIES = {"self_harm_ideation", "acute_medical", "abuse", "deportation_threat"}


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
        ts = datetime.now(timezone.utc).isoformat()
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

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Awaitable, Callable

import yaml
from fastapi import FastAPI
from pydantic import BaseModel

from .escalation import EscalationService
from .faq import FaqEntry, FaqIndex
from .identity import IdentityService
from .scheduler import Scheduler


class VerifyReq(BaseModel):
    call_id: str
    uin: str
    dob: str


class FaqReq(BaseModel):
    question: str


class BookReq(BaseModel):
    student_id: str
    appointment_type: str
    preferred_window: str


class EscalateReq(BaseModel):
    call_id: str
    caller_hash: str
    category: str
    severity: str
    summary: str
    last_turns: list[dict]
    trigger_layer: str


def create_app(
    *,
    data_dir: Path,
    seed_students: list[dict] | None = None,
    seed_faqs: list[dict] | None = None,
    embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]] | None = None,
) -> FastAPI:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    students = seed_students if seed_students is not None else _load_students()
    faqs_raw = seed_faqs if seed_faqs is not None else _load_faqs()
    faq_entries = [FaqEntry(**f) for f in faqs_raw]

    identity = IdentityService(students=students, max_attempts_per_call=3)
    scheduler = Scheduler(path=data_dir / "appointments.json")
    escalations = EscalationService(dir=data_dir / "escalations")

    if embed_fn is None:
        from ..config import Settings
        from .openai_embed import make_openai_embed
        embed_fn = make_openai_embed(Settings().openai_api_key)

    faq_index = FaqIndex(faq_entries, embed_fn=embed_fn)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if faq_entries:
            await faq_index.build()
        yield

    app = FastAPI(title="visavoice-backend", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.post("/identity/verify")
    async def verify(req: VerifyReq):
        r = identity.verify(call_id=req.call_id, uin=req.uin, dob=req.dob)
        return r.__dict__

    @app.post("/faq/lookup")
    async def faq_lookup(req: FaqReq):
        r = await faq_index.lookup(req.question)
        return {
            "match": r.match,
            "confidence": r.confidence,
            "entry": r.entry.__dict__ if r.entry else None,
        }

    @app.post("/appointments")
    async def book(req: BookReq):
        r = scheduler.book(
            student_id=req.student_id,
            appointment_type=req.appointment_type,
            preferred_window=req.preferred_window,
        )
        return r.__dict__

    @app.post("/escalation")
    async def escalate(req: EscalateReq):
        t = escalations.create(
            call_id=req.call_id, caller_hash=req.caller_hash,
            category=req.category, severity=req.severity,
            summary=req.summary, last_turns=req.last_turns,
            trigger_layer=req.trigger_layer,
        )
        return {"ticket_id": t.ticket_id}

    return app


def _load_students() -> list[dict]:
    path = Path(__file__).parent / "data" / "students.json"
    return json.loads(path.read_text())


def _load_faqs() -> list[dict]:
    path = Path(__file__).parent / "data" / "faqs.yaml"
    return yaml.safe_load(path.read_text())

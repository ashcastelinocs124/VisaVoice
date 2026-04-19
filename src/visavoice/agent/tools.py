import httpx


class ToolClient:
    """Thin HTTP wrapper around the FastAPI backend. All tools return dicts.

    On transport errors, returns a typed error dict rather than raising.
    """

    def __init__(self, base_url: str, call_id: str, caller_hash: str, timeout_s: float = 3.0):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_s)
        self._call_id = call_id
        self._caller_hash = caller_hash

    async def close(self) -> None:
        await self._client.aclose()

    async def _post(self, path: str, payload: dict, err_defaults: dict) -> dict:
        try:
            r = await self._client.post(path, json=payload)
            r.raise_for_status()
            return r.json()
        except httpx.TimeoutException:
            return {**err_defaults, "reason": "timeout"}
        except httpx.ConnectError:
            return {**err_defaults, "reason": "backend_down"}
        except httpx.HTTPStatusError as e:
            return {**err_defaults, "reason": f"http_{e.response.status_code}"}

    async def lookup_faq(self, question: str) -> dict:
        return await self._post("/faq/lookup", {"question": question},
                                err_defaults={"match": False, "entry": None, "confidence": 0.0})

    async def verify_identity(self, uin: str, dob: str) -> dict:
        return await self._post("/identity/verify",
                                {"call_id": self._call_id, "uin": uin, "dob": dob},
                                err_defaults={"verified": False})

    async def book_appointment(self, student_id: str, appointment_type: str, preferred_window: str) -> dict:
        return await self._post("/appointments",
                                {"student_id": student_id, "appointment_type": appointment_type,
                                 "preferred_window": preferred_window},
                                err_defaults={"booked": False})

    async def escalate_to_human(self, *, category: str, severity: str, summary: str,
                                 last_turns: list[dict], trigger_layer: str) -> dict:
        return await self._post("/escalation",
                                {"call_id": self._call_id, "caller_hash": self._caller_hash,
                                 "category": category, "severity": severity,
                                 "summary": summary, "last_turns": last_turns,
                                 "trigger_layer": trigger_layer},
                                err_defaults={"ticket_id": None})

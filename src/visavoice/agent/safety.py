from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from .safety_patterns import PATTERNS


SCRIPTS: dict[str, str] = {
    "self_harm_ideation": (
        "Thank you for telling me that. I want to make sure you get the right "
        "support right now, so I'm going to share a number with someone who "
        "can help. The UIUC Counseling Center crisis line is open 24/7. The "
        "number is 2-1-7, 3-3-3, 3-7-0-4. I'll say it once more: "
        "2-1-7, 3-3-3, 3-7-0-4. You can also reach the national 988 Suicide "
        "and Crisis Lifeline by dialing 9-8-8. Please call one of those "
        "numbers now. Take care."
    ),
    "sevis_termination": (
        "I'm sorry you're dealing with that. This needs an ISSS advisor "
        "directly. During business hours the number is 2-1-7, 3-3-3, 1-3-0-3. "
        "If it's outside business hours, please email isss@illinois.edu and "
        "an advisor will contact you first thing in the morning."
    ),
    "ice_contact": (
        "If immigration enforcement is at your location, please contact the "
        "UIUC Police non-emergency line at 2-1-7, 3-3-3, 8-9-1-1 and the ISSS "
        "emergency line at 2-1-7, 3-3-3, 1-3-0-3. You have rights — ask to "
        "speak to a lawyer before answering questions."
    ),
    "police_contact": (
        "Please focus on the situation in front of you. If this is an "
        "emergency, hang up and dial 9-1-1. Otherwise, ISSS can help "
        "afterward at 2-1-7, 3-3-3, 1-3-0-3."
    ),
    "abuse": (
        "I'm so sorry. Please reach out to the Women's Resources Center at "
        "2-1-7, 3-3-3, 3-1-3-7 or the national domestic violence hotline at "
        "1-8-0-0, 7-9-9, 7-2-3-3. If you are in immediate danger, please "
        "hang up and dial 9-1-1."
    ),
    "acute_medical": (
        "This sounds urgent. Please hang up and dial 9-1-1 right now, or go "
        "to the nearest emergency room."
    ),
    "deportation_threat": (
        "This needs an ISSS advisor immediately. The emergency ISSS line is "
        "2-1-7, 3-3-3, 1-3-0-3. Please call now. I'm also going to note this "
        "so an advisor can follow up."
    ),
}

HIGH_SEVERITY = {
    "self_harm_ideation", "acute_medical", "abuse",
    "deportation_threat", "ice_contact",
}


@dataclass(frozen=True)
class ScanResult:
    hit: bool
    category: Optional[str] = None
    severity: Optional[str] = None
    layer: Optional[str] = None
    script: Optional[str] = None


ClassifierFn = Callable[[str], Awaitable[Optional[str]]]


class Scanner:
    def __init__(self, classifier: ClassifierFn | None):
        self._classifier = classifier

    def scan_sync(self, utterance: str) -> ScanResult:
        for category, pattern in PATTERNS:
            if pattern.search(utterance):
                return ScanResult(
                    hit=True, category=category,
                    severity="high" if category in HIGH_SEVERITY else "medium",
                    layer="regex", script=SCRIPTS.get(category),
                )
        return ScanResult(hit=False)

    async def scan(self, utterance: str) -> ScanResult:
        regex = self.scan_sync(utterance)
        if regex.hit or self._classifier is None:
            return regex
        try:
            category = await self._classifier(utterance)
        except Exception:
            return ScanResult(hit=False)
        if category is None:
            return ScanResult(hit=False)
        return ScanResult(
            hit=True, category=category,
            severity="high" if category in HIGH_SEVERITY else "medium",
            layer="classifier", script=SCRIPTS.get(category),
        )

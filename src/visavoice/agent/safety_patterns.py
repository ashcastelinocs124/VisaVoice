import re

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("self_harm_ideation", re.compile(
        r"\b(i|i'?m|i\s+am)\s+("
        r"don'?t\s+want\s+to\s+(keep\s+going|live|go\s+on|be\s+here|do\s+this|exist)|"
        r"can'?t\s+(live|go\s+on|do\s+this)|"
        r"thinking\s+of\s+(ending|killing)|"
        r"want\s+to\s+(die|end\s+it|kill\s+myself)"
        r")\b",
        re.IGNORECASE,
    )),
    ("self_harm_ideation", re.compile(
        r"\b(ending\s+it\s+all|kill\s+myself|suicidal|end\s+my\s+life)\b",
        re.IGNORECASE,
    )),
    ("sevis_termination", re.compile(
        r"\b(my\s+)?sevis\s+(record\s+)?(was\s+|is\s+|got\s+)?(terminated|cancelled|ended)\b",
        re.IGNORECASE,
    )),
    ("ice_contact", re.compile(
        r"\b(ice|immigration\s+and\s+customs\s+enforcement)\s+("
        r"came|is\s+here|showed\s+up|arrested|detained|at\s+my|at\s+the)\b",
        re.IGNORECASE,
    )),
    ("police_contact", re.compile(
        r"\bpolice\s+(are\s+at|came\s+to|arrested|detained)\b",
        re.IGNORECASE,
    )),
    ("abuse", re.compile(
        r"\b(my\s+)?(partner|boyfriend|girlfriend|husband|wife|roommate)\s+"
        r"(hit|beat|hurt|threatened|is\s+abusing|abused)\s+me\b",
        re.IGNORECASE,
    )),
    ("acute_medical", re.compile(
        r"\b(chest\s+pain|can'?t\s+breathe|bleeding\s+heavily|overdosed|seizure)\b",
        re.IGNORECASE,
    )),
    ("deportation_threat", re.compile(
        r"\b(i(\s+am|'?m)\s+being\s+deported|they\s+(are|'?re)\s+deporting\s+me|"
        r"i\s+have\s+to\s+leave\s+the\s+country\s+(now|immediately))\b",
        re.IGNORECASE,
    )),
]

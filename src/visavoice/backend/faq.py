from dataclasses import dataclass
from typing import Awaitable, Callable
import math


EmbedFn = Callable[[list[str]], Awaitable[list[list[float]]]]


@dataclass(frozen=True)
class FaqEntry:
    id: str
    question: str
    answer: str
    citation_url: str


@dataclass(frozen=True)
class FaqLookupResult:
    match: bool
    entry: FaqEntry | None
    confidence: float


class FaqIndex:
    def __init__(self, entries: list[FaqEntry], embed_fn: EmbedFn, threshold: float = 0.7):
        self._entries = entries
        self._embed = embed_fn
        self._threshold = threshold
        self._vecs: list[list[float]] = []

    async def build(self) -> None:
        self._vecs = await self._embed([e.question for e in self._entries])

    async def lookup(self, query: str) -> FaqLookupResult:
        [qv] = await self._embed([query])
        best_i, best_sim = -1, -1.0
        for i, v in enumerate(self._vecs):
            sim = _cosine(qv, v)
            if sim > best_sim:
                best_i, best_sim = i, sim
        if best_sim < self._threshold:
            return FaqLookupResult(match=False, entry=None, confidence=best_sim)
        return FaqLookupResult(match=True, entry=self._entries[best_i], confidence=best_sim)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

from unittest.mock import AsyncMock
import pytest
from visavoice.backend.faq import FaqIndex, FaqEntry


@pytest.fixture
def entries():
    return [
        FaqEntry(id="opt_basics",     question="When can I apply for OPT?",         answer="…OPT…",           citation_url="u1"),
        FaqEntry(id="travel_sig",     question="Do I need a travel signature?",     answer="…travel sig…",    citation_url="u2"),
        FaqEntry(id="address_change", question="Do I need to report address change?", answer="…address…",     citation_url="u3"),
    ]


async def test_top_hit_above_threshold(entries):
    embed = AsyncMock(side_effect=[
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        [[1.0, 0.0, 0.0]],
    ])
    idx = FaqIndex(entries, embed_fn=embed)
    await idx.build()
    result = await idx.lookup("when can I get OPT")
    assert result.match is True
    assert result.entry.id == "opt_basics"
    assert result.confidence > 0.7


async def test_below_threshold_no_match(entries):
    embed = AsyncMock(side_effect=[
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        [[0.1, 0.1, 0.1]],
    ])
    idx = FaqIndex(entries, embed_fn=embed, threshold=0.7)
    await idx.build()
    result = await idx.lookup("totally unrelated question")
    assert result.match is False
    assert result.entry is None

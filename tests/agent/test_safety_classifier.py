from unittest.mock import AsyncMock

from visavoice.agent.safety import Scanner


async def test_classifier_miss_regex_hit():
    """When regex hits, classifier is never called."""
    classifier = AsyncMock()
    s = Scanner(classifier=classifier)
    r = await s.scan("i don't want to keep going anymore")
    assert r.hit is True
    assert r.layer == "regex"
    classifier.assert_not_called()


async def test_classifier_hit_when_regex_misses():
    classifier = AsyncMock(return_value="self_harm_ideation")
    s = Scanner(classifier=classifier)
    r = await s.scan("everything just feels too much and i'm tired of being alive")
    assert r.hit is True
    assert r.layer == "classifier"
    assert r.category == "self_harm_ideation"


async def test_classifier_miss():
    classifier = AsyncMock(return_value=None)
    s = Scanner(classifier=classifier)
    r = await s.scan("just wondering about library hours")
    assert r.hit is False


async def test_classifier_exception_is_non_hit():
    async def boom(_):
        raise RuntimeError("openai down")
    s = Scanner(classifier=boom)
    r = await s.scan("something innocent")
    assert r.hit is False

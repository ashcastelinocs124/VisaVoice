import pytest

from visavoice.agent.safety import Scanner

HITS = [
    ("i don't want to keep going anymore",          "self_harm_ideation"),
    ("i can't live like this",                       "self_harm_ideation"),
    ("thinking of ending it all",                    "self_harm_ideation"),
    ("my SEVIS record was terminated",               "sevis_termination"),
    ("ICE came to my apartment",                     "ice_contact"),
    ("police are at my door",                        "police_contact"),
    ("my partner hit me",                            "abuse"),
    ("chest pain and I can't breathe",               "acute_medical"),
]

MISSES = [
    "i could kill for some coffee right now",
    "i can live with that",
    "this terminates my bus route",
    "i saw some ice on the roof",
    "how do i get a police report for my visa",
    "i hit send on the email",
    "there's a pain in my schedule",
    "do i need to report a change of address",
    "when can i apply for OPT",
]


@pytest.fixture
def scanner():
    return Scanner(classifier=None)


@pytest.mark.parametrize("utterance,expected", HITS)
def test_hits(scanner, utterance, expected):
    result = scanner.scan_sync(utterance)
    assert result.hit is True
    assert result.category == expected


@pytest.mark.parametrize("utterance", MISSES)
def test_misses(scanner, utterance):
    result = scanner.scan_sync(utterance)
    assert result.hit is False

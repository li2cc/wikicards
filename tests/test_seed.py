import re

from wikicard import game

NAMES = None


def test_card_count_and_special_cards(seed_cards):
    assert len(seed_cards) == 45
    by_name = {c["name"]: c for c in seed_cards}
    first = seed_cards[0]
    assert first["name"] == "George Washington"
    assert first["years_in_office"] == "1789–1797" and first["party"] == "Unaffiliated"
    assert first["sort_order"] == 1
    cl = by_name["Grover Cleveland"]
    assert cl["years_in_office"] == "1885–1889, 1893–1897"
    assert cl["hint"].startswith("The 22nd and 24th president")
    assert by_name["Donald Trump"]["years_in_office"] == "2017–2021, 2025–present"
    assert by_name["William Henry Harrison"]["years_in_office"] == "1841"
    assert [c["sort_order"] for c in seed_cards] == list(range(1, 46))


def test_hints_do_not_leak_names(seed_cards):
    for c in seed_cards:
        parts = [p for p in re.findall(r"[A-Za-z]+", c["name"]) if len(p) > 2]
        for p in parts:
            assert p.lower() not in c["hint"].lower(), (c["name"], c["hint"])
        assert c["hint"].startswith("The ") and "president of the United States." in c["hint"]


def test_highlights(seed_cards):
    for c in seed_cards:
        assert 1 <= len(c["highlights"]) <= 5, c["name"]
        for h in c["highlights"]:
            assert h not in c["details"], (c["name"], h)
            assert len(h) <= 281


def test_every_card_answers_itself(seed_cards):
    names = [c["answer"] for c in seed_cards]
    for c in seed_cards:
        assert game.check_answer(c["answer"], c["answer"], names), c["name"]

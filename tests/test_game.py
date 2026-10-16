import pytest

from wikicard import game

NAMES = [
    "George Washington", "John Adams", "John Quincy Adams", "Abraham Lincoln",
    "Theodore Roosevelt", "Franklin D. Roosevelt", "George H. W. Bush", "George W. Bush",
    "Andrew Johnson", "Lyndon B. Johnson", "Harry S. Truman", "Grover Cleveland",
]


@pytest.mark.parametrize("guess,target,expected", [
    ("abraham lincoln", "Abraham Lincoln", True),
    ("Abraham Lincon", "Abraham Lincoln", True),
    ("Lincoln", "Abraham Lincoln", True),
    ("Franklin Roosevelt", "Franklin D. Roosevelt", True),
    ("Roosevelt", "Franklin D. Roosevelt", False),
    ("Roosevelt", "Theodore Roosevelt", False),
    ("George Bush", "George H. W. Bush", False),
    ("George Bush", "George W. Bush", False),
    ("George W Bush", "George W. Bush", True),
    ("George W Bush", "George H. W. Bush", False),
    ("John Adams", "John Quincy Adams", False),
    ("John Adams", "John Adams", True),
    ("John Quincy Adams", "John Quincy Adams", True),
    ("", "Abraham Lincoln", False),
    ("   ", "Abraham Lincoln", False),
    ("Harry Truman", "Harry S. Truman", True),
    ("Truman", "Harry S. Truman", True),
    ("President Lincoln", "Abraham Lincoln", True),
    ("Washington", "Abraham Lincoln", False),
    ("Johnson", "Andrew Johnson", False),
    ("Andrew Johnson", "Lyndon B. Johnson", False),
    ("Grover Cléveland", "Grover Cleveland", True),
])
def test_check_answer(guess, target, expected):
    assert game.check_answer(guess, target, NAMES) is expected


def test_quiz_score():
    assert game.quiz_score(3, 4) == 75.0
    assert game.quiz_score(0, 0) == 0
    assert game.quiz_score(1, 3) == 33.3


@pytest.mark.parametrize("elapsed,expected", [(0, 150), (10, 125), (20, 100), (20.5, 0)])
def test_points_correct(elapsed, expected):
    assert game.competition_points(True, elapsed) == expected


def test_points_wrong_and_max():
    assert game.competition_points(False, 1) == 0
    assert sum(game.competition_points(True, 0) for _ in range(10)) == game.MAX_COMP_SCORE == 1500


def test_ranking_and_ties():
    rows = [
        {"score": 900, "completion_time": 50, "date": 1},
        {"score": 1200, "completion_time": 60, "date": 2},
        {"score": 900, "completion_time": 40, "date": 3},
        {"score": 900, "completion_time": 40, "date": 0},
    ]
    ranked = game.rank_results(rows)
    assert [r["score"] for r in ranked] == [1200, 900, 900, 900]
    assert [(r["completion_time"], r["date"]) for r in ranked[1:]] == [(40, 0), (40, 3), (50, 1)]
    assert [r["rank"] for r in ranked] == [1, 2, 3, 4]


def test_ranking_limit():
    rows = [{"score": i, "completion_time": 1, "date": i} for i in range(30)]
    assert len(game.rank_results(rows)) == 20


def test_validate_registration():
    assert game.validate_registration("Ada", "Lovelace", "ada_1") == []
    assert game.validate_registration("", "L", "ada")
    assert game.validate_registration("A", "L", "ab")
    assert game.validate_registration("A", "L", "bad name!")
    assert game.validate_registration("A" * 41, "L", "adaa")

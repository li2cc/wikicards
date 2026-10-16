"""Game rules: answer checking, scoring, ranking, input validation."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

COMP_QUESTIONS = 10
COMP_SECONDS = 20
MAX_COMP_SCORE = COMP_QUESTIONS * 150
DROP_WORDS = {"jr", "sr", "president"}


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [t for t in text.split() if t not in DROP_WORDS]


def _forms(name: str) -> tuple[str, set[str]]:
    tokens = normalize(name)
    full = " ".join(tokens)
    core = [t for t in tokens if len(t) > 1] or tokens
    others = {" ".join(core)}
    if core:
        others.add(f"{core[0]} {core[-1]}")
    return full, others


def surname(name: str) -> str:
    tokens = normalize(name)
    return tokens[-1] if tokens else ""


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _best_similarity(guess: str, name: str) -> tuple[float, float]:
    full, others = _forms(name)
    return max(_sim(guess, f) for f in {full} | others), _sim(guess, full)


def check_answer(guess: str, card_name: str, all_names: list[str]) -> bool:
    tokens = normalize(guess)
    if not tokens:
        return False
    g = " ".join(tokens)
    names = list(dict.fromkeys(all_names))
    if card_name not in names:
        names.append(card_name)

    exact_full = [n for n in names if _forms(n)[0] == g]
    if exact_full:
        return card_name in exact_full
    short_owners = [n for n in names if g in _forms(n)[1]]
    if short_owners:
        return short_owners == [card_name]

    if len(tokens) == 1:
        sn = surname(card_name)
        if any(surname(n) == sn for n in names if n != card_name):
            return False
        return _sim(g, sn) >= 0.88

    scores = {n: _best_similarity(g, n) for n in names}
    mine = scores[card_name]
    if mine[0] < 0.85:
        return False
    return all(mine > s for n, s in scores.items() if n != card_name)


def quiz_score(correct: int, attempted: int) -> float:
    if attempted <= 0:
        return 0.0
    return round(100 * correct / attempted, 1)


def speed_bonus(elapsed: float) -> int:
    if elapsed > COMP_SECONDS:
        return 0
    return int(50 * (1 - max(elapsed, 0) / COMP_SECONDS) + 0.5)


def competition_points(correct: bool, elapsed: float) -> int:
    if not correct or elapsed > COMP_SECONDS:
        return 0
    return 100 + speed_bonus(elapsed)


def rank_results(rows: list[dict], limit: int | None = 20) -> list[dict]:
    """Order by score desc, completion_time asc, date asc; add a 1-based rank."""
    ordered = sorted(rows, key=lambda r: (-r["score"], r["completion_time"], r["date"]))
    if limit is not None:
        ordered = ordered[:limit]
    return [{**r, "rank": i} for i, r in enumerate(ordered, start=1)]


USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,30}$")


def validate_registration(first: str, last: str, username: str) -> list[str]:
    errors = []
    if not 1 <= len(first.strip()) <= 40:
        errors.append("First name must be 1–40 characters.")
    if not 1 <= len(last.strip()) <= 40:
        errors.append("Last name must be 1–40 characters.")
    if not USERNAME_RE.match(username.strip()):
        errors.append("Username must be 3–30 characters: letters, digits, '.', '_' or '-'.")
    return errors


def medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

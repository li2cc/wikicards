"""Pure text helpers: years, ordinals, sentence splitting, hints and highlights."""
from __future__ import annotations

import re

ABBREVIATIONS = {
    "u.s", "u.k", "jr", "sr", "st", "mr", "mrs", "ms", "dr", "gen", "col", "lt", "sen",
    "rep", "gov", "no", "vs", "capt", "maj", "sgt", "rev", "hon", "prof", "mt", "ft",
    "inc", "co", "corp", "d.c", "a.d", "b.c", "e.g", "i.e", "etc", "ph.d", "u.s.a",
}

_SENT_END = re.compile(r"(?<=[.!?])[\"”’)]*\s+(?=[\"“‘(]*[A-Z0-9])")


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def ordinal_phrase(numbers: list[int]) -> str:
    parts = [ordinal(n) for n in numbers]
    if len(parts) <= 1:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 2 else " and ".join(parts)


def format_years(terms: list[tuple[int, int | None]]) -> str:
    """Each term is (start_year, end_year); end None means the incumbent."""
    out = []
    for start, end in terms:
        if end is None:
            out.append(f"{start}–present")
        elif start == end:
            out.append(str(start))
        else:
            out.append(f"{start}–{end}")
    return ", ".join(out)


def parse_term(text: str) -> tuple[int, int | None] | None:
    years = [int(y) for y in re.findall(r"\b(1[78]\d\d|19\d\d|20\d\d)\b", text)]
    if not years:
        return None
    start = years[0]
    if re.search(r"incumbent|present", text, re.I):
        return start, None
    return start, years[-1]


def clean_text(text: str) -> str:
    text = re.sub(r"\s*\[[^\]]*\]", "", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    return text.strip()


def split_sentences(paragraph: str) -> list[str]:
    paragraph = paragraph.strip()
    if not paragraph:
        return []
    pieces = _SENT_END.split(paragraph)
    sentences: list[str] = []
    for piece in pieces:
        if sentences and _ends_with_abbreviation(sentences[-1]):
            sentences[-1] = sentences[-1] + " " + piece
        else:
            sentences.append(piece)
    return [s.strip() for s in sentences if s.strip()]


def _ends_with_abbreviation(sentence: str) -> bool:
    match = re.search(r"([A-Za-z.]+)\.$", sentence)
    if not match:
        return False
    token = match.group(1).lower().lstrip(".")
    if token in ABBREVIATIONS:
        return True
    # Single initials such as "Franklin D." or "John F."
    return len(token) == 1 and sentence[-3:-2] == " " and token.isalpha()


def paragraphs(extract: str) -> list[str]:
    return [clean_text(p) for p in extract.split("\n") if p.strip()]


def name_parts(name: str) -> list[str]:
    name = re.sub(r"\(.*?\)", "", name)
    parts = re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", name)
    return [p for p in parts if len(p) > 2]


def mask_name(sentence: str, name: str) -> str:
    out = sentence
    for part in sorted(set(name_parts(name)), key=len, reverse=True):
        out = re.sub(rf"(?<!\w){re.escape(part)}(?!\w)", "_____", out, flags=re.I)
    return out


def _leaks_name(text: str, name: str) -> bool:
    low = text.lower()
    return any(p.lower() in low for p in name_parts(name))


def build_hint(numbers: list[int], name: str, lead_paragraphs: list[str]) -> str:
    head = f"The {ordinal_phrase(numbers)} president of the United States."
    candidates: list[str] = []
    if lead_paragraphs:
        candidates.extend(split_sentences(lead_paragraphs[0])[1:])
        for para in lead_paragraphs[1:]:
            candidates.extend(split_sentences(para))
    for sentence in candidates:
        masked = mask_name(sentence, name)
        if 40 <= len(masked) <= 300 and not _leaks_name(masked.replace("_____", ""), name):
            if masked.count("_____") > 3:
                continue
            return f"{head} {masked}"
    return head


STRONG = [
    "first", "only", "youngest", "oldest", "longest", "shortest", "landslide", "assassinated",
    "impeached", "Nobel", "Proclamation", "Amendment", "Doctrine", "Treaty", "Act", "signed",
    "declared", "resigned", "unanimously", "purchase", "emancipation", "acquired", "Deal",
]
MEDIUM = [
    "led", "won", "defeated", "war", "reform", "crisis", "appointed", "established", "passed",
    "negotiated", "expanded", "created", "ordered", "vetoed", "elected", "victory", "policy",
    "economy", "recession", "invasion", "controversy", "scandal",
]
FILLER = [
    "born", "graduated", "married", "buried", "died", "educated", "raised", "grew",
    "attended", "enrolled", "family", "son", "daughter", "wife", "father", "mother",
]
_CAP_SENSITIVE = {"Nobel", "Proclamation", "Amendment", "Doctrine", "Treaty", "Act", "Deal"}
_STOP_LEAD = {
    "As", "In", "The", "He", "His", "After", "During", "When", "While", "Following", "Under",
    "Although", "Despite", "By", "At", "On", "For", "With", "Before", "However", "Since",
    "This", "That", "These", "Those", "Upon", "Throughout", "Having", "Both", "Many",
}


def _kw_hit(word: str, text: str) -> bool:
    flags = 0 if word in _CAP_SENSITIVE else re.I
    return re.search(rf"\b{re.escape(word)}s?\b", text, flags) is not None


def score_sentence(sentence: str) -> int:
    score = 0
    score += 3 * sum(_kw_hit(w, sentence) for w in STRONG)
    score += 1 * sum(_kw_hit(w, sentence) for w in MEDIUM)
    if re.search(r"\bAs president\b|\bhis administration\b|\bHis administration\b|\bpresidency\b",
                 sentence, re.I):
        score += 2
    score -= 4 * sum(_kw_hit(w, sentence) for w in FILLER)
    if len(sentence) > 260:
        score -= 2
    return score


def _multiword_names(sentence: str, own_parts: set[str]) -> set[str]:
    names = set()
    for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", sentence):
        tokens = match.group(0).split()
        while tokens and tokens[0] in _STOP_LEAD:
            tokens.pop(0)
        if len(tokens) < 2 or any(t.lower() in own_parts for t in tokens):
            continue
        names.add(" ".join(tokens))
    return names


def shorten(sentence: str, limit: int = 280) -> str:
    if len(sentence) <= limit:
        return sentence
    window = sentence[: limit - 1]
    cut = max(window.rfind(","), window.rfind(";"))
    if cut < 60:
        cut = window.rfind(" ")
    return sentence[:cut].rstrip(",; ") + "…"


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", s).strip().lower()


def build_highlights(name: str, lead_paragraphs: list[str], max_items: int = 5) -> list[str]:
    own = {p.lower() for p in name_parts(name)}
    description = _norm(lead_paragraphs[0]) if lead_paragraphs else ""
    candidates: list[tuple[int, int, str]] = []
    index = 0
    for para in lead_paragraphs[1:]:
        for sentence in split_sentences(para):
            if 50 <= len(sentence) <= 400 and sentence[0].isupper():
                if _norm(sentence) not in description:
                    candidates.append((score_sentence(sentence), index, sentence))
                    index += 1
    ranked = sorted((c for c in candidates if c[0] > 0), key=lambda c: (-c[0], c[1]))
    chosen: list[tuple[int, str]] = []
    used_names: set[str] = set()
    for _, idx, sentence in ranked:
        names = _multiword_names(sentence, own)
        if names & used_names:
            continue
        chosen.append((idx, sentence))
        used_names |= names
        if len(chosen) == max_items:
            break
    chosen.sort()
    return [shorten(s) for _, s in chosen]

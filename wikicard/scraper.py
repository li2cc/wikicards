"""Collect US president cards from Wikipedia (with a bundled JSON fallback)."""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

from . import textproc

log = logging.getLogger(__name__)

LIST_URL = "https://en.wikipedia.org/wiki/List_of_presidents_of_the_United_States"
API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = (
    "WikiCardLearningSystem/1.0 (https://github.com/li2cc/wikicards; student study app) "
    "python-requests"
)
CATEGORY = "US Presidents"
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_us_presidents.json"
BATCH_SIZE = 20


def http_get(url: str, params: dict | None = None, retries: int = 5, timeout: int = 20,
             sleep=time.sleep) -> requests.Response:
    """GET with a descriptive User-Agent; retries 429/5xx with exponential backoff."""
    delay = 1.0
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT},
                                timeout=timeout)
        except requests.RequestException as exc:
            last = exc
        else:
            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("Retry-After", "")
                wait = float(retry_after) if retry_after.isdigit() else delay
                last = requests.HTTPError(f"HTTP {resp.status_code} from {url}")
                if attempt < retries - 1:
                    sleep(min(wait, 30))
                delay *= 2
                continue
            resp.raise_for_status()
            return resp
        if attempt < retries - 1:
            sleep(delay)
        delay *= 2
    raise last or RuntimeError("request failed")


def _clean_cell(cell) -> str:
    for junk in cell.select("sup, style, .reference"):
        junk.decompose()
    return re.sub(r"\s+", " ", cell.get_text(" ", strip=True))


def parse_presidents_table(html: str) -> list[dict]:
    """One dict per presidency (47 rows): number, name, link, image, party, term."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for table in soup.select("table.wikitable"):
        for tr in table.select("tr"):
            th = tr.find("th", attrs={"scope": "row"})
            if th is None or not th.get_text(strip=True).isdigit():
                continue
            cells = tr.find_all("td", recursive=False)
            if len(cells) < 5:
                continue
            number = int(th.get_text(strip=True))
            img = cells[0].find("img")
            image_url = ""
            if img is not None and img.get("src"):
                image_url = img["src"]
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                image_url = re.sub(r"/\d+px-", "/330px-", image_url).split("?")[0]
            link = cells[1].select_one("b a[href]") or cells[1].find("a", href=True)
            name = link.get_text(strip=True) if link else ""
            href = link["href"] if link else ""
            term = textproc.parse_term(_clean_cell(cells[2]))
            party = _clean_cell(cells[4])
            party = re.sub(r"-\s+", "-", party).strip()
            if not (name and href and term):
                continue
            rows.append({"number": number, "name": name, "href": href, "image_url": image_url,
                         "party": party, "term": term})
    return rows


def title_from_href(href: str) -> str:
    return unquote(urlparse(href).path.rsplit("/", 1)[-1]).replace("_", " ")


def merge_rows(rows: list[dict]) -> list[dict]:
    """Merge non-consecutive terms of the same person into one entry."""
    merged: dict[str, dict] = {}
    for row in rows:
        key = row["href"]
        if key not in merged:
            merged[key] = {**row, "numbers": [row["number"]], "terms": [row["term"]],
                           "parties": [row["party"]]}
        else:
            entry = merged[key]
            entry["numbers"].append(row["number"])
            entry["terms"].append(row["term"])
            if row["party"] not in entry["parties"]:
                entry["parties"].append(row["party"])
            if not entry["image_url"]:
                entry["image_url"] = row["image_url"]
    return sorted(merged.values(), key=lambda e: e["numbers"][0])


def fetch_leads(titles: list[str], http=http_get) -> dict[str, dict]:
    """Return {requested title: {'extract': str, 'image': str}} using batched API calls."""
    result: dict[str, dict] = {}
    for i in range(0, len(titles), BATCH_SIZE):
        batch = titles[i:i + BATCH_SIZE]
        resp = http(API_URL, params={
            "action": "query", "format": "json", "formatversion": 2, "redirects": 1,
            "prop": "extracts|pageimages", "exintro": 1, "explaintext": 1, "exlimit": "max",
            "piprop": "thumbnail", "pithumbsize": 330, "titles": "|".join(batch),
        })
        query = resp.json().get("query", {})
        alias: dict[str, str] = {}
        for item in query.get("normalized", []) + query.get("redirects", []):
            alias[item["from"]] = item["to"]
        pages = {p.get("title"): p for p in query.get("pages", [])}
        for title in batch:
            target = title
            for _ in range(3):
                target = alias.get(target, target)
            page = pages.get(target)
            if page and page.get("extract"):
                result[title] = {"extract": page["extract"],
                                 "image": (page.get("thumbnail") or {}).get("source", "")}
    return result


def build_cards(rows: list[dict], leads: dict[str, dict]) -> list[dict]:
    cards = []
    for order, entry in enumerate(merge_rows(rows), start=1):
        title = title_from_href(entry["href"])
        lead = leads.get(title, {})
        paras = textproc.paragraphs(lead.get("extract", ""))
        highlights = textproc.build_highlights(entry["name"], paras)
        cards.append({
            "name": entry["name"],
            "image_url": entry["image_url"] or lead.get("image", ""),
            "category": CATEGORY,
            "hint": textproc.build_hint(entry["numbers"], entry["name"], paras),
            "answer": entry["name"],
            "details": paras[0] if paras else "",
            "highlights": highlights,
            "party": " / ".join(entry["parties"]),
            "years_in_office": textproc.format_years(entry["terms"]),
            "sort_order": order,
            "source_url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
        })
    return cards


def harvest_from_wikipedia(http=http_get) -> list[dict]:
    html = http(LIST_URL).text
    rows = parse_presidents_table(html)
    if len(rows) < 40:
        raise RuntimeError(f"Unexpected Wikipedia table layout ({len(rows)} rows parsed)")
    titles = []
    for row in merge_rows(rows):
        titles.append(title_from_href(row["href"]))
    leads = fetch_leads(titles, http=http)
    return build_cards(rows, leads)


def load_seed(path: Path = SEED_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def harvest(http=http_get) -> tuple[list[dict], str]:
    """Return (cards, source) where source is 'wikipedia' or 'seed'."""
    try:
        cards = harvest_from_wikipedia(http)
        if len(cards) >= 40 and all(c["details"] for c in cards):
            return cards, "wikipedia"
        log.warning("Wikipedia harvest incomplete; using bundled snapshot")
    except Exception as exc:  # network, parsing, rate limit
        log.warning("Wikipedia harvest failed (%s); using bundled snapshot", exc)
    return load_seed(), "seed"


def write_seed(cards: list[dict], path: Path = SEED_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cards, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    data = harvest_from_wikipedia()
    write_seed(data)
    print(f"Wrote {len(data)} cards to {SEED_PATH}")

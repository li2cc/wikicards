import json

import pytest
import requests

from wikicard import scraper

TABLE = """
<table class="wikitable"><tr><th scope="col">No.</th></tr>
<tr><th scope="row" rowspan="2"><a href="/x">22</a></th><td><img src="//up.wikimedia.org/a/330px-x.jpg?utm=1"></td>
<td><b><a href="https://en.wikipedia.org/wiki/Grover_Cleveland">Grover Cleveland</a></b> (1837–1908)<sup>[1]</sup></td>
<td>March 4, 1885 – March 4, 1889</td><td></td><td>Democratic</td><td>1884</td><td>x</td></tr>
<tr><th scope="row"><a href="/y">23</a></th><td></td>
<td><b><a href="https://en.wikipedia.org/wiki/Benjamin_Harrison">Benjamin Harrison</a></b></td>
<td>March 4, 1889 – March 4, 1893</td><td></td><td>Republican</td><td>1888</td><td>x</td></tr>
<tr><th scope="row"><a href="/z">24</a></th><td></td>
<td><b><a href="https://en.wikipedia.org/wiki/Grover_Cleveland">Grover Cleveland</a></b></td>
<td>March 4, 1893 – March 4, 1897</td><td></td><td>Democratic</td><td>1892</td><td>x</td></tr>
</table>"""


def test_parse_and_merge():
    rows = scraper.parse_presidents_table(TABLE)
    assert [r["number"] for r in rows] == [22, 23, 24]
    assert rows[0]["image_url"] == "https://up.wikimedia.org/a/330px-x.jpg"
    merged = scraper.merge_rows(rows)
    assert len(merged) == 2
    assert merged[0]["numbers"] == [22, 24]
    assert merged[0]["terms"] == [(1885, 1889), (1893, 1897)]


def test_fetch_leads_batches_of_20():
    calls = []

    class R:
        def __init__(self, params):
            titles = params["titles"].split("|")
            self._d = {"query": {"pages": [{"title": t, "extract": f"{t} lead."} for t in titles]}}

        def json(self):
            return self._d

    def http(url, params=None):
        calls.append(params)
        return R(params)

    titles = [f"T{i}" for i in range(45)]
    out = scraper.fetch_leads(titles, http=http)
    assert len(calls) == 3 and len(out) == 45
    assert all(len(c["titles"].split("|")) <= 20 for c in calls)


def test_http_get_retries_429(monkeypatch):
    statuses = [429, 429, 200]
    sleeps = []

    class Resp:
        def __init__(self, code):
            self.status_code, self.headers, self.text = code, {}, "ok"

        def raise_for_status(self):
            pass

    def fake_get(url, params=None, headers=None, timeout=None):
        assert "User-Agent" in headers and "WikiCard" in headers["User-Agent"]
        return Resp(statuses.pop(0))

    monkeypatch.setattr(scraper.requests, "get", fake_get)
    resp = scraper.http_get("http://x", sleep=sleeps.append)
    assert resp.status_code == 200 and sleeps == [1.0, 2.0]


def test_harvest_falls_back_to_seed(monkeypatch, seed_cards):
    def boom(*a, **k):
        raise requests.ConnectionError("offline")

    cards, source = scraper.harvest(http=boom)
    assert source == "seed" and cards == seed_cards

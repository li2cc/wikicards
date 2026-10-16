from datetime import datetime, timedelta, timezone

from wikicard.ui import results

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _quiz(days):
    return [{"username": "a", "score": 50.0 + i, "date": NOW + timedelta(days=i)} for i in days]


def test_quiz_chart_dots_vs_daily_line():
    dots = results.quiz_chart(_quiz([0, 0, 1]))
    assert dots.data[0].mode == "markers" and len(dots.data[0].x) == 3
    line = results.quiz_chart(_quiz([0, 1, 2, 2]))
    assert line.data[0].mode == "lines+markers" and len(line.data[0].x) == 3
    assert list(line.layout.yaxis.range) == [0, 100] and not line.layout.showlegend


def test_distribution_and_top_students():
    rows = [{"username": u, "score": s} for u, s in [("a", 900), ("a", 1200), ("b", 1000)]]
    dist = results.distribution_chart(rows)
    assert dist.data[0].xbins.size == 100 and list(dist.layout.xaxis.range) == [0, 1500]
    top = results.top_students_chart(rows)
    assert top.data[0].orientation == "h"
    assert list(top.data[0].x)[-1] == 1200 and top.data[0].text is not None

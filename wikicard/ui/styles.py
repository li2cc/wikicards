"""Global CSS and small HTML helpers."""
from __future__ import annotations

from html import escape

import streamlit as st

CSS = """
<style>
:root { --primary:#2a78d6; --bg:#f7f8fb; --bg2:#eef2f8; --text:#0f172a; }
.block-container { padding-top: 3.2rem; max-width: 1100px; }
.hero { background: linear-gradient(135deg,#2a78d6 0%,#1d4ea8 100%); color:#fff;
  padding: 1.4rem 1.6rem; border-radius: 18px; margin-bottom: 1.2rem;
  box-shadow: 0 8px 24px rgba(42,120,214,.25); }
.hero h1 { color:#fff; margin:0; padding:0; font-size:1.9rem; line-height:1.2; }
.hero p { margin:.3rem 0 0 0; opacity:.92; font-size:1.02rem; }
.wc-card { display:flex; gap:1.4rem; background:#fff; border-radius:18px; padding:1.3rem;
  box-shadow:0 6px 22px rgba(15,23,42,.10); align-items:flex-start; }
.wc-card.back { border-top:5px solid var(--primary); }
.wc-portrait { width:190px; min-width:190px; aspect-ratio:3/4; object-fit:cover;
  border-radius:12px; background:var(--bg2); }
.wc-body { flex:1; min-width:0; }
.wc-body h2 { margin:0 0 .4rem 0; padding:0; font-size:1.6rem; }
.chip { display:inline-block; background:var(--bg2); color:#1d4ea8; border-radius:999px;
  padding:.2rem .75rem; margin:0 .4rem .4rem 0; font-size:.88rem; font-weight:600; }
.wc-hint { font-size:1.05rem; margin-top:.6rem; }
.wc-records { background:#e8f1fc; border-left:4px solid var(--primary); border-radius:10px;
  padding:.7rem 1rem; margin-top:.8rem; }
.wc-records b { display:block; margin-bottom:.2rem; }
.wc-records ul { margin:.2rem 0 0 1.1rem; padding:0; }
.wc-records li { margin-bottom:.35rem; }
.wc-link a { color:var(--primary); font-weight:600; text-decoration:none; }
div[data-testid="stMetric"] { background:#fff; border-radius:14px; padding:.7rem .9rem;
  box-shadow:0 3px 12px rgba(15,23,42,.06); }
html, body, [data-testid="stAppViewContainer"] { overflow-x:hidden; }
@media (max-width: 640px) {
  .block-container { padding: 4.2rem .8rem 2rem .8rem; }
  .wc-card { flex-direction:column; align-items:center; text-align:center; }
  .wc-card .wc-body { width:100%; }
  .wc-records { text-align:left; }
  .hero h1 { font-size:1.5rem; }
  .wc-portrait { min-width:0; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',
                unsafe_allow_html=True)


def chips(*items: str) -> str:
    return "".join(f'<span class="chip">{escape(i)}</span>' for i in items if i)


def portrait(url: str | None) -> str:
    return f'<img class="wc-portrait" src="{escape(url or "", quote=True)}" alt="Portrait">'


def card_front_html(card: dict) -> str:
    return (f'<div class="wc-card">{portrait(card.get("image_url"))}<div class="wc-body">'
            f'{chips(card.get("years_in_office"), card.get("party"))}'
            f'<div class="wc-hint">💡 {escape(card.get("hint") or "")}</div></div></div>')


def card_back_html(card: dict) -> str:
    records = ""
    if card.get("highlights"):
        items = "".join(f"<li>{escape(h)}</li>" for h in card["highlights"])
        records = f'<div class="wc-records"><b>Most notable records</b><ul>{items}</ul></div>'
    link = ""
    if card.get("source_url"):
        link = (f'<p class="wc-link"><a href="{escape(card["source_url"], quote=True)}" '
                f'target="_blank" rel="noopener">Read more on Wikipedia →</a></p>')
    return (f'<div class="wc-card back">{portrait(card.get("image_url"))}<div class="wc-body">'
            f'<h2>{escape(card["name"])}</h2>'
            f'{chips(card.get("years_in_office"), card.get("party"))}'
            f'<p>{escape(card.get("details") or "")}</p>{records}{link}</div></div>')

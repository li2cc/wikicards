"""Study page: flip through the cards."""
from __future__ import annotations

import random

import streamlit as st

from . import services
from .styles import card_back_html, card_front_html, hero


def _go(db, total: int, idx: int) -> None:
    st.session_state["study_idx"] = idx % total
    st.session_state["study_jump"] = idx % total
    st.session_state["study_show"] = False
    st.session_state["study_seen"].add(idx % total)
    st.session_state["study_viewed"] += 1
    uid = services.current_user_id()
    if uid is not None:
        db.add_card_view(uid)


def _on_jump(db, total: int) -> None:
    _go(db, total, st.session_state["study_jump"])


def _toggle() -> None:
    st.session_state["study_show"] = not st.session_state["study_show"]


def render() -> None:
    db = services.get_db()
    cards = services.load_cards(db)
    hero("Study", "Flip through the cards and learn each president.")
    if not cards:
        st.warning("There are no cards yet. An administrator can build the database "
                   "on the **Build Database** page.")
        return
    total = len(cards)
    ss = st.session_state
    if "study_idx" not in ss:
        ss.update(study_idx=0, study_jump=0, study_show=False, study_seen=set(),
                  study_viewed=0)
        _go(db, total, 0)
    idx = min(ss["study_idx"], total - 1)
    card = cards[idx]

    m = st.columns(3)
    m[0].metric("Card", f"{idx + 1} / {total}")
    m[1].metric("Viewed this session", ss["study_viewed"])
    m[2].metric("Unique cards seen", f"{len(ss['study_seen'])} / {total}")
    st.progress(len(ss["study_seen"]) / total)

    b = st.columns(4)
    b[0].button("Previous", on_click=_go, args=(db, total, idx - 1), use_container_width=True)
    b[1].button("Hide Answer" if ss["study_show"] else "Show Answer", on_click=_toggle,
                type="primary", use_container_width=True)
    b[2].button("Next", on_click=_go, args=(db, total, idx + 1), use_container_width=True)
    b[3].button("Random", on_click=lambda: _go(db, total, random.randrange(total)),
                use_container_width=True)

    st.markdown(card_back_html(card) if ss["study_show"] else card_front_html(card),
                unsafe_allow_html=True)
    ss["study_jump"] = idx
    st.selectbox("Jump to a card", list(range(total)), key="study_jump",
                 format_func=lambda i: f"#{i + 1}", on_change=_on_jump, args=(db, total))

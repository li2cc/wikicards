"""Timed competition page (server-side timing)."""
from __future__ import annotations

import random
import time

import pandas as pd
import streamlit as st

from .. import game
from . import services
from .styles import card_front_html, hero


def _new(cards: list[dict]) -> None:
    st.session_state["comp"] = {
        "order": random.sample(range(len(cards)), game.COMP_QUESTIONS), "i": 0, "score": 0,
        "correct": 0, "time": 0.0, "rows": [], "last": None, "done": False, "saved": False,
        "start": time.monotonic(),
    }


def _answer(comp: dict, card: dict, guess: str | None, names: list[str]) -> None:
    elapsed = time.monotonic() - comp["start"]
    right = bool(guess) and game.check_answer(guess, card["answer"], names)
    on_time = elapsed <= game.COMP_SECONDS
    ok = right and on_time
    points = game.competition_points(right, elapsed)
    bonus = game.speed_bonus(elapsed) if ok else 0
    comp["score"] += points
    comp["correct"] += int(ok)
    comp["time"] += min(elapsed, game.COMP_SECONDS)
    comp["rows"].append({
        "#": comp["i"] + 1, "Answer": guess or "(no answer)", "Correct answer": card["answer"],
        "Result": "✅" if ok else "❌", "Time (s)": round(min(elapsed, game.COMP_SECONDS), 1),
        "Points": points})
    comp["last"] = {"ok": ok, "points": points, "bonus": bonus, "answer": card["answer"],
                    "guess": guess, "timeout": guess is None, "late": right and not on_time}


def _next(db, uid: int, comp: dict) -> None:
    comp["i"] += 1
    comp["last"] = None
    comp["start"] = time.monotonic()
    if comp["i"] >= game.COMP_QUESTIONS:
        comp["done"] = True
        if not comp["saved"]:
            db.save_competition_result(uid, comp["score"], comp["correct"], comp["time"])
            comp["saved"] = True


def _timer(comp: dict, card: dict, names: list[str]) -> None:
    """Live countdown; submits automatically as wrong when time runs out."""
    remaining = game.COMP_SECONDS - (time.monotonic() - comp["start"])
    if remaining <= 0:
        _answer(comp, card, None, names)
        st.rerun()
    bonus = game.speed_bonus(game.COMP_SECONDS - remaining)
    st.progress(max(0.0, min(1.0, remaining / game.COMP_SECONDS)),
                text=f"⏱️ {int(remaining + 0.999)}s left · speed bonus now ≈ {bonus}")


def render() -> None:
    db = services.get_db()
    hero("Competition", "Ten questions, 20 seconds each. Faster answers earn more points.")
    uid = services.require_login(db)
    cards = services.load_cards(db)
    if len(cards) < game.COMP_QUESTIONS:
        st.warning(f"At least {game.COMP_QUESTIONS} cards are needed to compete.")
        return
    comp = st.session_state.get("comp")

    if comp is None:
        st.write("Answer 10 random presidents. Points: 100 for a correct answer plus up to "
                 "50 speed bonus. Maximum score 1500.")
        st.button("Start competition", type="primary", on_click=_new, args=(cards,))
        return

    if comp["done"]:
        st.success(f"🏁 Finished! Final score {comp['score']} · {comp['correct']}/"
                   f"{game.COMP_QUESTIONS} correct · {comp['time']:.1f} s total answer time.")
        st.dataframe(pd.DataFrame(comp["rows"]), hide_index=True, use_container_width=True)
        if comp["correct"] == game.COMP_QUESTIONS and not comp.get("balloons"):
            comp["balloons"] = True
            st.balloons()
        if st.button("Play again"):
            st.session_state.pop("comp")
            st.rerun()
        return

    card = cards[comp["order"][comp["i"]]]
    names = [c["answer"] for c in cards]
    m = st.columns(3)
    m[0].metric("Question", f"{comp['i'] + 1} / {game.COMP_QUESTIONS}")
    m[1].metric("Score", comp["score"])
    m[2].metric("Correct", comp["correct"])
    st.markdown(card_front_html(card), unsafe_allow_html=True)

    last = comp["last"]
    if last is None:
        st.fragment(run_every=1)(_timer)(comp, card, names)
        with st.form(f"comp_form_{comp['i']}", clear_on_submit=True):
            guess = st.text_input("Who is this president?")
            submitted = st.form_submit_button("Submit", type="primary")
        if submitted:
            _answer(comp, card, guess, names)
            st.rerun()
    else:
        if last["ok"]:
            st.success(f"✅ Correct! It's {last['answer']}. **+{last['points']} points** "
                       f"(100 + {last['bonus']} speed bonus)")
        elif last["timeout"]:
            st.error(f"⏰ Time's up! The right answer is {last['answer']}. +0 points")
        elif last["late"]:
            st.error(f"❌ Too slow! The right answer is {last['answer']}. +0 points")
        else:
            st.error(f'❌ Incorrect. You answered "{last["guess"]}". '
                     f"The right answer is {last['answer']}. +0 points")
        st.button("Next question", type="primary", on_click=_next, args=(db, uid, comp))

    if st.button("Quit competition"):
        st.session_state.pop("comp")
        st.rerun()

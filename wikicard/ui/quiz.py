"""Quiz page."""
from __future__ import annotations

import random

import pandas as pd
import streamlit as st

from .. import game
from . import services
from .styles import card_front_html, hero


def _start(cards: list[dict], choice) -> None:
    n = len(cards) if choice == "All" else min(int(choice), len(cards))
    st.session_state["quiz"] = {
        "order": random.sample(range(len(cards)), n), "i": 0, "attempted": 0, "correct": 0,
        "rows": [], "feedback": None, "done": False, "saved": False,
    }


def _record(qz: dict, card: dict, guess: str, correct: bool, skipped: bool) -> None:
    qz["attempted"] += 1
    qz["correct"] += int(correct)
    shown = "(I don't know)" if skipped else guess
    qz["rows"].append({"#": qz["i"] + 1, "Your answer": shown, "Correct answer": card["answer"],
                       "Result": "✅" if correct else "❌"})
    if correct:
        qz["feedback"] = ("success", f"✅ Correct! It's {card['answer']}.")
    else:
        qz["feedback"] = ("error", f'❌ Incorrect. You answered "{shown}". '
                                   f"The right answer is {card['answer']}.")


def _finish(db, uid: int, qz: dict) -> None:
    qz["done"] = True
    if qz["attempted"] > 0 and not qz["saved"]:
        score = game.quiz_score(qz["correct"], qz["attempted"])
        db.save_quiz_result(uid, score, qz["attempted"], qz["correct"])
        qz["saved"] = True


def _next(db, uid: int, qz: dict) -> None:
    qz["i"] += 1
    qz["feedback"] = None
    if qz["i"] >= len(qz["order"]):
        _finish(db, uid, qz)


def render() -> None:
    db = services.get_db()
    hero("Quiz", "Name the president from the portrait and the clues.")
    uid = services.require_login(db)
    cards = services.load_cards(db)
    if not cards:
        st.warning("There are no cards yet.")
        return
    qz = st.session_state.get("quiz")

    if qz is None:
        choice = st.segmented_control("Number of questions", [5, 10, 20, "All"], default=10)
        st.button("Start quiz", type="primary", disabled=choice is None,
                  on_click=_start, args=(cards, choice))
        return

    if qz["done"]:
        pct = game.quiz_score(qz["correct"], qz["attempted"])
        if qz["saved"]:
            st.success(f"Quiz complete! You scored {qz['correct']} / {qz['attempted']} "
                       f"({pct:.1f}%). Result saved.")
        else:
            st.info("Quiz ended with no answers, so nothing was saved.")
        if qz["rows"]:
            st.dataframe(pd.DataFrame(qz["rows"]), hide_index=True, use_container_width=True)
        if st.button("Start a new quiz"):
            st.session_state.pop("quiz")
            st.rerun()
        return

    total = len(qz["order"])
    card = cards[qz["order"][qz["i"]]]
    names = [c["answer"] for c in cards]
    m = st.columns(4)
    m[0].metric("Question", f"{qz['i'] + 1} / {total}")
    m[1].metric("Attempted", qz["attempted"])
    m[2].metric("Correct", qz["correct"])
    m[3].metric("Incorrect", qz["attempted"] - qz["correct"])

    st.markdown(card_front_html(card), unsafe_allow_html=True)
    answered = qz["feedback"] is not None
    if answered:
        kind, msg = qz["feedback"]
        (st.success if kind == "success" else st.error)(msg)
        st.button("Next question", type="primary", on_click=_next, args=(db, uid, qz))
    else:
        with st.form(f"quiz_form_{qz['i']}", clear_on_submit=True):
            guess = st.text_input("Who is this president?")
            c1, c2 = st.columns(2)
            check = c1.form_submit_button("Check answer", type="primary",
                                          use_container_width=True)
            skip = c2.form_submit_button("I don't know", use_container_width=True)
        if check or skip:
            ok = check and game.check_answer(guess, card["answer"], names)
            _record(qz, card, guess, ok, skipped=skip)
            st.rerun()

    if st.button("End quiz & save"):
        _finish(db, uid, qz)
        st.rerun()

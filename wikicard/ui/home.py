"""Home page: metrics, registration and login."""
from __future__ import annotations

import streamlit as st

from .. import game
from ..db import UsernameTaken
from . import services
from .styles import hero


def _login_form(db) -> None:
    users = db.list_users()
    labels = {u["id"]: f"{u['username']} — {u['first_name']} {u['last_name']}" for u in users}
    with st.form("login"):
        choice = st.selectbox("Select your account", list(labels), index=None,
                              format_func=labels.get, placeholder="Choose an account")
        if st.form_submit_button("Log in", type="primary"):
            if choice is None:
                st.warning("Please select an account.")
            else:
                st.session_state["user_id"] = choice
                db.touch_login(choice)
                st.rerun()


def _register_form(db) -> None:
    with st.form("register"):
        first = st.text_input("First name", max_chars=40)
        last = st.text_input("Last name", max_chars=40)
        username = st.text_input("Username", max_chars=30,
                                 help="3–30 characters: letters, digits, '.', '_' or '-'")
        if st.form_submit_button("Create profile", type="primary"):
            errors = game.validate_registration(first, last, username)
            if errors:
                for e in errors:
                    st.error(e)
                return
            try:
                uid = db.create_user(first, last, username)
            except UsernameTaken as exc:
                st.error(str(exc))
                return
            st.session_state["user_id"] = uid
            st.rerun()


def render() -> None:
    db = services.get_db()
    hero("WikiCard Learning System", "Study, quiz and compete: can you name every US president?")
    uid = services.current_user_id()
    stats = db.home_stats(uid)
    c = st.columns(4)
    c[0].metric("Study cards", stats["cards"])
    c[1].metric("Students", stats["students"])
    c[2].metric("Quizzes taken", stats["quizzes"])
    c[3].metric("Top competition score", stats["top_score"])

    if uid is not None and "mine" in stats:
        user = db.get_user(uid)
        st.subheader(f"Welcome back, {user['first_name']}!")
        mine = stats["mine"]
        c = st.columns(4)
        c[0].metric("Cards viewed", mine["viewed"] or 0)
        c[1].metric("Quizzes completed", mine["quizzes"])
        c[2].metric("Average quiz score %", f"{mine['avg_quiz']:.1f}")
        c[3].metric("Best competition", mine["best_comp"])
        return

    st.subheader("Get started")
    login_tab, register_tab = st.tabs(["Log in", "Register"])
    with login_tab:
        _login_form(db)
    with register_tab:
        _register_form(db)

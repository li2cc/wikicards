"""Streamlit-bound services: cached DB, bootstrap, session helpers, admin gate."""
from __future__ import annotations

import os

import streamlit as st

from .. import scraper
from ..db import Database, get_database_url

TOPICS = {
    "US Presidents": True,
    "State Capitals (coming soon)": False,
    "Countries (coming soon)": False,
    "National Parks (coming soon)": False,
    "Programming Languages (coming soon)": False,
}
DEFAULT_TOPIC = "US Presidents"


@st.cache_resource(show_spinner="Connecting to the database…")
def get_db() -> Database:
    """Connect, create tables, and harvest once per server start if there are no cards."""
    db = Database(get_database_url())
    db.init_schema()
    if db.count_cards(scraper.CATEGORY) == 0:
        harvest_into(db)
    return db


def harvest_into(db: Database, delete_first: bool = False) -> tuple[int, str]:
    if delete_first:
        db.delete_cards(scraper.CATEGORY)
    cards, source = scraper.harvest()
    db.replace_cards(scraper.CATEGORY, cards)
    load_cards.clear()
    return len(cards), source


@st.cache_data(ttl=300, show_spinner=False)
def load_cards(_db: Database, category: str = scraper.CATEGORY) -> list[dict]:
    return _db.list_cards(category)


def current_user_id() -> int | None:
    return st.session_state.get("user_id")


def require_login(db: Database) -> int:
    uid = current_user_id()
    if uid is None or db.get_user(uid) is None:
        st.session_state.pop("user_id", None)
        st.info("Please log in or create a profile on the **Home** page first.")
        st.stop()
    return uid


def require_admin() -> None:
    """Ask for ADMIN_PASSWORD when that secret/env var is set."""
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not password:
        try:
            password = str(st.secrets.get("ADMIN_PASSWORD", ""))
        except Exception:
            password = ""
    if not password or st.session_state.get("admin_ok"):
        return
    with st.form("admin_login"):
        entered = st.text_input("Admin password", type="password")
        if st.form_submit_button("Unlock"):
            if entered == password:
                st.session_state["admin_ok"] = True
                st.rerun()
            st.error("Incorrect password.")
    st.stop()

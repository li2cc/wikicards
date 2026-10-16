"""Build Database, Admin and Setup pages."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import scraper
from ..db import describe_url
from . import services
from .styles import hero


def _topic_gate(topic: str) -> bool:
    if not services.TOPICS.get(topic, False):
        st.info(f"**{topic.replace(' (coming soon)', '')}** is coming soon.")
        return False
    return True


def _report(count: int, source: str) -> None:
    where = "Wikipedia" if source == "wikipedia" else "the bundled snapshot (Wikipedia was unreachable)"
    st.success(f"Loaded {count} cards from {where}.")


def build() -> None:
    db = services.get_db()
    hero("Build Database", "Collect the cards for a topic from Wikipedia.")
    services.require_admin()
    topic = st.radio("Choose a topic", list(services.TOPICS), index=0)
    if not _topic_gate(topic):
        return
    existing = db.count_cards(scraper.CATEGORY)
    st.write(f"Cards currently in the database: **{existing}**")
    label = "Refresh Database" if existing else "Build database"
    if st.button(label, type="primary"):
        with st.spinner("Collecting cards from Wikipedia…"):
            count, source = services.harvest_into(db)
        _report(count, source)


def admin() -> None:
    db = services.get_db()
    hero("Admin", "Database overview and maintenance.")
    services.require_admin()

    st.caption(describe_url(db.url))
    counts, sizes = db.table_counts(), db.table_sizes_kb()
    st.subheader("Tables")
    st.dataframe(pd.DataFrame({"Table": list(counts), "Rows": list(counts.values()),
                               "Size (KB)": [sizes[t] for t in counts]}),
                 hide_index=True, use_container_width=True)
    st.subheader("Cards per category")
    cats = db.category_counts()
    if cats:
        st.dataframe(pd.DataFrame(cats).rename(columns={"category": "Category",
                                                         "cards": "Cards"}),
                     hide_index=True, use_container_width=True)
    else:
        st.info("There are no cards in the database.")

    st.subheader("Maintain cards")
    topic = st.selectbox("Topic", list(services.TOPICS))
    if not _topic_gate(topic):
        return
    c1, c2 = st.columns(2)
    if c1.button("Refresh"):
        with st.spinner("Refreshing…"):
            _report(*services.harvest_into(db))
    if c2.button("Rebuild"):
        with st.spinner("Rebuilding…"):
            _report(*services.harvest_into(db, delete_first=True))
    st.divider()
    sure = st.checkbox("I understand this can't be undone")
    if st.button("Delete all cards", disabled=not sure):
        db.delete_cards(scraper.CATEGORY)
        services.load_cards.clear()
        st.warning("All cards deleted. Use Refresh or Rebuild to bring them back.")


def setup(error: Exception) -> None:
    hero("Setup needed", "The app could not reach its PostgreSQL database.")
    st.error(f"{type(error).__name__}: {error}")
    st.markdown(
        "**How to fix it**\n"
        "1. In Supabase open *Project Settings → Database → Connection string* and copy the "
        "**Session pooler** URI (IPv4; do not use the `db.*.supabase.co` host).\n"
        "2. Set it as `DATABASE_URL` in `.streamlit/secrets.toml` (see "
        "`secrets.toml.example`) or as an environment variable.\n"
        "3. Optionally run `supabase/schema.sql` in the Supabase SQL editor.")
    if st.button("Retry connection", type="primary"):
        st.rerun()

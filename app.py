"""WikiCard Learning System - Streamlit entry point."""
from pathlib import Path

import streamlit as st

from wikicard.ui import competition, home, manage, quiz, results, services, study
from wikicard.ui.styles import inject_css

ROOT = Path(__file__).parent

st.set_page_config(page_title="WikiCard", page_icon=":material/style:", layout="wide")
inject_css()
st.logo(str(ROOT / "assets" / "logo.svg"), size="large")

try:
    db = services.get_db()
except Exception as exc:  # show the real error on a setup page
    st.navigation([st.Page(lambda: manage.setup(exc), title="Setup",
                           icon=":material/settings:", url_path="setup")]).run()
    st.stop()

pages = {
    "Learn": [
        st.Page(home.render, title="Home", icon=":material/home:", default=True),
        st.Page(study.render, title="Study", icon=":material/menu_book:", url_path="study"),
        st.Page(quiz.render, title="Quiz", icon=":material/quiz:", url_path="quiz"),
        st.Page(competition.render, title="Competition", icon=":material/timer:",
                url_path="competition"),
    ],
    "Results": [
        st.Page(results.leaderboard, title="Leaderboard", icon=":material/leaderboard:",
                url_path="leaderboard"),
        st.Page(results.analytics, title="Analytics", icon=":material/bar_chart:",
                url_path="analytics"),
    ],
    "Manage": [
        st.Page(manage.build, title="Build Database", icon=":material/database:",
                url_path="build"),
        st.Page(manage.admin, title="Admin", icon=":material/admin_panel_settings:",
                url_path="admin"),
    ],
}

with st.sidebar:
    uid = services.current_user_id()
    user = db.get_user(uid) if uid else None
    if user:
        st.caption(f"Signed in as **{user['username']}**")
        if st.button("Log out", icon=":material/logout:", use_container_width=True):
            for key in list(st.session_state):
                del st.session_state[key]
            st.rerun()

st.navigation(pages).run()

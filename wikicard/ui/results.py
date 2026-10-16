"""Leaderboard and Analytics pages."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .. import game
from . import services
from .styles import hero

BLUE = "#2a78d6"
GRID = "rgba(15,23,42,0.08)"
SORTS = ["Rank", "Student Name", "Score", "Date"]


def _default_order() -> None:
    st.session_state["lb_order"] = ("Descending" if st.session_state["lb_sort"]
                                    in ("Score", "Date") else "Ascending")


def leaderboard() -> None:
    db = services.get_db()
    hero("Leaderboard", "The top 20 competition results.")
    summary = db.leaderboard_summary()
    c = st.columns(3)
    c[0].metric("Highest score ever", summary["best"])
    c[1].metric("Average score", f"{summary['average']:.0f}")
    c[2].metric("Total players", summary["players"])

    rows = game.rank_results(db.leaderboard(20))
    if not rows:
        st.info("No competition results yet. Be the first to compete!")
        return
    if "lb_sort" not in st.session_state:
        st.session_state["lb_sort"] = "Rank"
        st.session_state["lb_order"] = "Ascending"
    s1, s2 = st.columns(2)
    s1.selectbox("Sort by", SORTS, key="lb_sort", on_change=_default_order)
    s2.selectbox("Order", ["Ascending", "Descending"], key="lb_order")

    df = pd.DataFrame([{
        "rank": r["rank"], "Student Name": f"{r['first_name']} {r['last_name']}",
        "Score": r["score"], "correct": r["correct_answers"], "Time (s)": r["completion_time"],
        "Date": pd.Timestamp(r["date"]),
    } for r in rows])
    key = {"Rank": "rank", "Student Name": "Student Name", "Score": "Score", "Date": "Date"}[
        st.session_state["lb_sort"]]
    df = df.sort_values(key, ascending=st.session_state["lb_order"] == "Ascending",
                        kind="stable", key=(lambda s: s.str.lower()) if key == "Student Name"
                        else None)
    out = pd.DataFrame({
        "Rank": df["rank"].map(game.medal), "Student Name": df["Student Name"],
        "Score": df["Score"], "Correct": df["correct"].map(lambda n: f"{n} / 10"),
        "Time (s)": df["Time (s)"].round(1), "Date": df["Date"].dt.strftime("%Y-%m-%d %H:%M"),
    })
    st.dataframe(out, hide_index=True, use_container_width=True)


def _style(fig: go.Figure, xtitle: str, ytitle: str) -> go.Figure:
    fig.update_layout(
        showlegend=False, plot_bgcolor="#fff", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10), xaxis_title=xtitle, yaxis_title=ytitle,
        font=dict(color="#0f172a"))
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


def quiz_chart(rows: list[dict]) -> go.Figure:
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    days = df["date"].dt.date.nunique()
    if days >= 3:
        daily = df.groupby(df["date"].dt.date)["score"].mean().round(1).reset_index()
        fig = go.Figure(go.Scatter(
            x=daily["date"], y=daily["score"], mode="lines+markers",
            line=dict(color=BLUE), marker=dict(color=BLUE),
            hovertemplate="%{x|%b %d, %Y}<br>Average score: %{y:.1f}%<extra></extra>"))
        xt = "Date"
    else:
        fig = go.Figure(go.Scatter(
            x=df["date"], y=df["score"], mode="markers", marker=dict(color=BLUE, size=10),
            customdata=df[["username"]],
            hovertemplate="%{x|%b %d, %Y %H:%M}<br>Score: %{y:.1f}%<br>"
                          "Student: %{customdata[0]}<extra></extra>"))
        xt = "Date taken"
    fig = _style(fig, xt, "Quiz score (%)")
    fig.update_yaxes(range=[0, 100])
    fig.update_xaxes(tickformat="%b %d" if days >= 3 else "%b %d, %H:%M")
    return fig


def distribution_chart(rows: list[dict]) -> go.Figure:
    scores = [r["score"] for r in rows]
    fig = go.Figure(go.Histogram(
        x=scores, xbins=dict(start=0, end=1500, size=100), marker=dict(color=BLUE),
        hovertemplate="Score range starting %{x}<br>Games: %{y}<extra></extra>"))
    fig = _style(fig, "Competition score (100-point bins)", "Number of games")
    fig.update_xaxes(range=[0, 1500], dtick=100)
    return fig


def top_students_chart(rows: list[dict]) -> go.Figure:
    df = pd.DataFrame(rows).groupby("username")["score"].max().sort_values(
        ascending=False).head(10).iloc[::-1]
    fig = go.Figure(go.Bar(
        x=df.values, y=df.index, orientation="h", marker=dict(color=BLUE), text=df.values,
        textposition="outside", hovertemplate="%{y}<br>Best score: %{x}<extra></extra>"))
    fig = _style(fig, "Best competition score", "Student")
    fig.update_xaxes(range=[0, 1650])
    return fig


def analytics() -> None:
    db = services.get_db()
    hero("Analytics", "How the class is doing across quizzes and competitions.")
    s = db.analytics_summary()
    c = st.columns(5)
    c[0].metric("Total users", s["users"])
    c[1].metric("Total cards", s["cards"])
    c[2].metric("Quizzes taken", s["quizzes"])
    c[3].metric("Avg quiz score", f"{s['avg_quiz']:.1f}%")
    c[4].metric("Avg competition score", f"{s['avg_comp']:.0f}")

    quizzes, comps = db.quiz_rows(), db.competition_rows()

    st.subheader("Quiz scores over time")
    if quizzes:
        st.plotly_chart(quiz_chart(quizzes), use_container_width=True)
        st.caption("Each dot is one quiz; once quizzes span three or more days, the line shows "
                   "the daily average score.")
    else:
        st.info("No quizzes have been taken yet.")

    st.subheader("Competition score distribution")
    if comps:
        st.plotly_chart(distribution_chart(comps), use_container_width=True)
        st.caption("How many competition games landed in each 100-point score range "
                   "(the maximum is 1500).")
    else:
        st.info("No competitions have been played yet.")

    st.subheader("Top performing students")
    if comps:
        st.plotly_chart(top_students_chart(comps), use_container_width=True)
        st.caption("Each student's best competition score; the top 10 are shown.")
    else:
        st.info("No competitions have been played yet.")

    with st.expander("Raw quiz results"):
        st.dataframe(pd.DataFrame(quizzes), hide_index=True, use_container_width=True)
    with st.expander("Raw competition results"):
        st.dataframe(pd.DataFrame(comps), hide_index=True, use_container_width=True)

"""PostgreSQL access (psycopg 3 + psycopg-pool) for the WikiCard app."""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg import errors as pg_errors
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
TABLES = ["users", "userprofiles", "cards", "quizresults", "competitionresults"]
CONNECT_TIMEOUT = 8


class UsernameTaken(Exception):
    pass


class DatabaseConfigError(Exception):
    pass


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        try:
            import streamlit as st

            url = str(st.secrets.get("DATABASE_URL", "")).strip()
        except Exception:
            url = ""
    if not url:
        raise DatabaseConfigError(
            "DATABASE_URL is not set. Add it to the environment or to .streamlit/secrets.toml "
            "(use the Supabase Session pooler connection string)."
        )
    return url


def describe_url(url: str) -> str:
    """Host/port/database without credentials."""
    parsed = urlparse(url)
    return f"PostgreSQL · {parsed.hostname}:{parsed.port or 5432}{parsed.path or '/postgres'}"


class Database:
    def __init__(self, url: str, min_size: int = 1, max_size: int = 4):
        self.url = url
        # Fail fast with the real error before building a pool.
        with psycopg.connect(url, connect_timeout=CONNECT_TIMEOUT):
            pass
        self.pool = ConnectionPool(
            url, min_size=min_size, max_size=max_size, open=False, timeout=CONNECT_TIMEOUT,
            kwargs={"row_factory": dict_row, "connect_timeout": CONNECT_TIMEOUT,
                    "prepare_threshold": None},
        )
        self.pool.open(wait=True, timeout=CONNECT_TIMEOUT + 2)

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def conn(self):
        with self.pool.connection() as c:
            yield c

    def query(self, sql: str, params=None) -> list[dict]:
        with self.conn() as c:
            return c.execute(sql, params).fetchall()

    def one(self, sql: str, params=None) -> dict | None:
        with self.conn() as c:
            return c.execute(sql, params).fetchone()

    def execute(self, sql: str, params=None) -> None:
        with self.conn() as c:
            c.execute(sql, params)

    # ---------- schema ----------
    def init_schema(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        with self.conn() as c:
            c.execute(sql)

    # ---------- users ----------
    def create_user(self, first: str, last: str, username: str) -> int:
        first, last, username = first.strip(), last.strip(), username.strip()
        try:
            with self.conn() as c:
                row = c.execute(
                    "insert into users (first_name, last_name, username) values (%s, %s, %s) "
                    "returning id", (first, last, username)).fetchone()
                c.execute(
                    "insert into userprofiles (user_id, display_name, last_login) "
                    "values (%s, %s, now())", (row["id"], f"{first} {last}"))
                return row["id"]
        except pg_errors.UniqueViolation:
            raise UsernameTaken(f"The username '{username}' is already taken.") from None

    def list_users(self) -> list[dict]:
        return self.query(
            "select id, username, first_name, last_name from users order by lower(username)")

    def get_user(self, user_id: int) -> dict | None:
        return self.one(
            "select u.id, u.username, u.first_name, u.last_name, p.display_name, "
            "p.cards_viewed from users u join userprofiles p on p.user_id = u.id "
            "where u.id = %s", (user_id,))

    def touch_login(self, user_id: int) -> None:
        self.execute("update userprofiles set last_login = now() where user_id = %s", (user_id,))

    def add_card_view(self, user_id: int) -> None:
        self.execute(
            "update userprofiles set cards_viewed = cards_viewed + 1 where user_id = %s",
            (user_id,))

    # ---------- cards ----------
    def count_cards(self, category: str | None = None) -> int:
        if category:
            row = self.one("select count(*) as n from cards where category = %s", (category,))
        else:
            row = self.one("select count(*) as n from cards")
        return row["n"]

    def list_cards(self, category: str) -> list[dict]:
        return self.query("select * from cards where category = %s order by sort_order",
                          (category,))

    def replace_cards(self, category: str, cards: list[dict]) -> None:
        with self.conn() as c:
            c.execute("delete from cards where category = %s", (category,))
            with c.cursor() as cur:
                cur.executemany(
                    "insert into cards (name, image_url, category, hint, answer, details, "
                    "highlights, party, years_in_office, sort_order, source_url) "
                    "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    [(x["name"], x.get("image_url"), category, x["hint"], x["answer"],
                      x.get("details"), Jsonb(x.get("highlights", [])), x.get("party"),
                      x.get("years_in_office"), x["sort_order"], x.get("source_url"))
                     for x in cards])

    def delete_cards(self, category: str) -> None:
        self.execute("delete from cards where category = %s", (category,))

    # ---------- results ----------
    def save_quiz_result(self, user_id: int, score: float, attempted: int, correct: int) -> None:
        self.execute(
            "insert into quizresults (user_id, score, questions_attempted, correct_answers) "
            "values (%s, %s, %s, %s)", (user_id, score, attempted, correct))

    def save_competition_result(self, user_id: int, score: int, correct: int,
                                completion_time: float) -> None:
        self.execute(
            "insert into competitionresults (user_id, score, correct_answers, completion_time) "
            "values (%s, %s, %s, %s)", (user_id, score, correct, round(completion_time, 2)))

    def leaderboard(self, limit: int = 20) -> list[dict]:
        return self.query(
            "select r.id, u.username, u.first_name, u.last_name, r.score, r.correct_answers, "
            "r.completion_time::float8 as completion_time, r.date "
            "from competitionresults r join users u on u.id = r.user_id "
            "order by r.score desc, r.completion_time asc, r.date asc limit %s", (limit,))

    def leaderboard_summary(self) -> dict:
        return self.one(
            "select coalesce(max(score), 0) as best, coalesce(avg(score), 0)::float8 as average, "
            "count(distinct user_id) as players from competitionresults")

    # ---------- statistics ----------
    def home_stats(self, user_id: int | None) -> dict:
        stats = self.one(
            "select (select count(*) from cards) as cards, "
            "(select count(*) from users) as students, "
            "(select count(*) from quizresults) as quizzes, "
            "(select coalesce(max(score), 0) from competitionresults) as top_score")
        if user_id:
            stats["mine"] = self.one(
                "select (select cards_viewed from userprofiles where user_id = %(u)s) as viewed, "
                "(select count(*) from quizresults where user_id = %(u)s) as quizzes, "
                "(select coalesce(avg(score), 0)::float8 from quizresults "
                "  where user_id = %(u)s) as avg_quiz, "
                "(select coalesce(max(score), 0) from competitionresults "
                "  where user_id = %(u)s) as best_comp", {"u": user_id})
        return stats

    def quiz_rows(self) -> list[dict]:
        return self.query(
            "select q.id, u.username, q.score::float8 as score, q.questions_attempted, "
            "q.correct_answers, q.date from quizresults q join users u on u.id = q.user_id "
            "order by q.date")

    def competition_rows(self) -> list[dict]:
        return self.query(
            "select r.id, u.username, r.score, r.correct_answers, "
            "r.completion_time::float8 as completion_time, r.date "
            "from competitionresults r join users u on u.id = r.user_id order by r.date")

    def analytics_summary(self) -> dict:
        return self.one(
            "select (select count(*) from users) as users, (select count(*) from cards) as cards, "
            "(select count(*) from quizresults) as quizzes, "
            "(select coalesce(avg(score), 0)::float8 from quizresults) as avg_quiz, "
            "(select coalesce(avg(score), 0)::float8 from competitionresults) as avg_comp")

    def table_counts(self) -> dict[str, int]:
        return {t: self.one(f"select count(*) as n from {t}")["n"] for t in TABLES}

    def table_sizes_kb(self) -> dict[str, float]:
        return {t: round(self.one("select pg_total_relation_size(%s::regclass) as s",
                                  (t,))["s"] / 1024, 1) for t in TABLES}

    def category_counts(self) -> list[dict]:
        return self.query(
            "select category, count(*) as cards from cards group by category order by category")

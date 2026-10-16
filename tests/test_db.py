"""Database tests: run only when TEST_DATABASE_URL is set; each run uses a throw-away schema."""
import os
import uuid

import psycopg
import pytest

from wikicard import db as dbmod

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture()
def database():
    schema = "t_" + uuid.uuid4().hex[:10]
    with psycopg.connect(URL, autocommit=True) as c:
        c.execute(f"create schema {schema}")
    sep = "&" if "?" in URL else "?"
    d = dbmod.Database(f"{URL}{sep}options=-csearch_path%3D{schema}")
    d.init_schema()
    yield d
    d.close()
    with psycopg.connect(URL, autocommit=True) as c:
        c.execute(f"drop schema {schema} cascade")


def test_registration_and_case_insensitive_unique(database):
    uid = database.create_user("Ada", "Lovelace", "ada")
    assert database.get_user(uid)["display_name"] == "Ada Lovelace"
    with pytest.raises(dbmod.UsernameTaken, match="The username 'ADA' is already taken."):
        database.create_user("Other", "Person", "ADA")
    assert len(database.list_users()) == 1


def test_rls_enabled_on_all_tables(database):
    rows = database.query(
        "select relname, relrowsecurity from pg_class "
        "where relnamespace = current_schema()::regnamespace and relkind = 'r'")
    flags = {r["relname"]: r["relrowsecurity"] for r in rows}
    assert set(dbmod.TABLES) <= set(flags) and all(flags[t] for t in dbmod.TABLES)


def test_cards_roundtrip_and_delete(database, seed_cards):
    database.replace_cards("US Presidents", seed_cards)
    assert database.count_cards() == 45
    cards = database.list_cards("US Presidents")
    assert cards[0]["name"] == "George Washington" and isinstance(cards[0]["highlights"], list)
    database.delete_cards("US Presidents")
    assert database.count_cards() == 0


def test_results_leaderboard_and_stats(database):
    a = database.create_user("A", "One", "user_a")
    b = database.create_user("B", "Two", "user_b")
    database.save_competition_result(a, 900, 7, 80.5)
    database.save_competition_result(b, 1200, 9, 90.0)
    database.save_competition_result(a, 900, 7, 70.0)
    board = database.leaderboard()
    assert [(r["score"], r["completion_time"]) for r in board] == [(1200, 90.0), (900, 70.0),
                                                                   (900, 80.5)]
    database.save_quiz_result(a, 75.0, 4, 3)
    stats = database.home_stats(a)
    assert stats["quizzes"] == 1 and stats["mine"]["avg_quiz"] == 75.0
    assert stats["mine"]["best_comp"] == 900
    database.add_card_view(a)
    database.add_card_view(a)
    assert database.get_user(a)["cards_viewed"] == 2


def test_constraints(database):
    uid = database.create_user("A", "One", "user_a")
    with pytest.raises(psycopg.errors.CheckViolation):
        database.save_competition_result(uid, 1501, 5, 10)
    with pytest.raises(psycopg.errors.CheckViolation):
        database.create_user("A", "One", "bad name")


def test_describe_url_hides_password():
    text = dbmod.describe_url("postgresql://u:secret@aws-0-x.pooler.supabase.com:5432/postgres")
    assert text == "PostgreSQL · aws-0-x.pooler.supabase.com:5432/postgres"

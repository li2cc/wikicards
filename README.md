# WikiCard Learning System

IT6108 Demonstration (full-stack web app). A Streamlit app that helps students learn the US
presidents: study cards, quizzes, a timed competition with a leaderboard, and analytics. Card
data is collected from Wikipedia by the app itself and stored in PostgreSQL (Supabase).

## Layout

| Path | Purpose |
| --- | --- |
| `app.py` | Streamlit entry point (navigation, sidebar, setup page on DB errors) |
| `wikicard/scraper.py` | Wikipedia table + MediaWiki API harvest, JSON-snapshot fallback |
| `wikicard/textproc.py` | Years, hints, rule-based highlights |
| `wikicard/game.py` | Answer checking, scoring, ranking, validation |
| `wikicard/db.py` | psycopg 3 + psycopg-pool data access |
| `wikicard/ui/` | Streamlit pages and styling |
| `supabase/schema.sql` | Tables, CHECKs, indexes, RLS (also applied on startup) |
| `data/seed_us_presidents.json` | Bundled snapshot used if Wikipedia is unreachable |

## Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit it
streamlit run app.py
```

`DATABASE_URL` may be set as an environment variable or in `.streamlit/secrets.toml`. If it is
missing or the connection fails, a setup page shows the real error.
`ADMIN_PASSWORD` (optional) protects the *Build Database* and *Admin* pages.

## Supabase setup

1. Create a free Supabase project.
2. *Project Settings → Database → Connection string → **Session pooler*** and copy the URI
   (IPv4). Do **not** use the `db.<ref>.supabase.co` host (IPv6-only).
3. Put it in `DATABASE_URL`. Tables are created on startup; you can also run
   `supabase/schema.sql` in the SQL editor. RLS is enabled on all tables with no policies, so
   the public REST API (`/rest/v1/cards`) returns `[]`.

## Deploy (Streamlit Community Cloud)

Point it at this repo with `app.py` as the main file and paste the contents of your
`secrets.toml` into the app's *Secrets*. Do not set `server.port`.

On first start with an empty `cards` table the app harvests Wikipedia once (45 cards from the
list page plus 3 batched article-lead API requests). After that, only *Refresh* / *Rebuild*
re-harvest; "Delete all cards" stays deleted until rebuilt. To regenerate the bundled snapshot:
`python -m wikicard.scraper`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Database tests run only when `TEST_DATABASE_URL` is set; each test uses a throw-away schema that
is dropped afterwards. Point it at a scratch database, never the real one.

# News Agent

A news aggregation web app — BBC, NPR, The Guardian, Nikkei Asia & SCMP →
Gemini summary + topic + importance → filterable feed with thumbnails.

## How to run locally

```bash
export GEMINI_API_KEY="your_key"
uv run uvicorn main:app --reload
```

Then open http://localhost:8000. Click **Refresh** to fetch.

- **First refresh** scrapes 5 sources, fetches og:images concurrently,
  runs one batched Gemini analysis call — typically under 30s.
- **Subsequent refreshes** are much faster: URLs already in the DB skip both
  the image fetch and the Gemini call.

## Storage

Articles persist in `news.db` (SQLite). `/api/news` returns the rolling
24h window — fresh refreshes accumulate rather than replace, so an
important article from 5h ago stays visible on the next refresh.

## Structure

- `main.py` — FastAPI app, two endpoints (`GET /api/news`, `POST /api/refresh`)
- `fetcher.py` — scraping, og:image extraction, batched Gemini analysis
- `db.py` — SQLite layer (`init_db`, `save_articles`, `get_recent_articles`)
- `static/index.html` — vanilla-JS frontend
- `news.db` — local store, gitignored

## Deployment

The app is set up for Railway out of the box (`Procfile` + `railway.json`).
The same Procfile works on any Heroku-style platform; for Fly.io, add a
`fly.toml` pointing at the same start command.

**Required env vars:**

| Variable          | Required | Default     | Notes |
| ----------------- | -------- | ----------- | ----- |
| `GEMINI_API_KEY`  | yes      | —           | Get from https://aistudio.google.com/apikey |
| `DATABASE_PATH`   | no       | `./news.db` | Override when the platform mounts persistent storage at a fixed path (e.g. `/data/news.db` on Fly.io volumes). Parent dirs are created automatically. |
| `PORT`            | no       | `8000`      | Platforms set this at runtime — `Procfile` / `railway.json` pass it to uvicorn via `--port $PORT`. |

**Note on storage:** SQLite needs a persistent disk to survive restarts.
On platforms with ephemeral filesystems (default on Railway, Fly, Render
without a volume), `news.db` is wiped on every deploy / restart. For a
production deploy, attach a volume and point `DATABASE_PATH` at it.

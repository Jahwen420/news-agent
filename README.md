# News Agent

A news aggregation web app — BBC, NPR, The Guardian, Nikkei Asia & SCMP →
Gemini summary + topic + importance → filterable feed with thumbnails.

## How to run

```bash
export GEMINI_API_KEY="your_key"
uv run uvicorn main:app --reload
```

Then open http://localhost:8000. Click 🔄 to refresh.

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

# News Agent

A daily news aggregation agent — built as I learn Python and agent workflows.

Aggregates BBC, NPR & The Guardian → runs each headline through Gemini for a
one-sentence summary, topic and importance label → serves a filterable web UI.

## How to run

```bash
export GEMINI_API_KEY="your_key"
uv run uvicorn main:app --reload
```

Then open http://localhost:8000. Click 🔄 to fetch (~2 minutes for 15 headlines).

## Structure

- `main.py` — FastAPI app, two endpoints: `GET /api/news`, `POST /api/refresh`
- `fetcher.py` — scraping + Gemini analyze
- `static/index.html` — vanilla-JS frontend
- `cache.json` — latest fetched payload (gitignored)

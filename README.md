# Loop. — AI News Brief

> Stay in the loop. An AI-powered news aggregator that curates what's
> worth knowing today — with editorial framing, political bias indicators,
> and multilingual support.

## Live Demo

[https://web-production-40a5.up.railway.app](https://web-production-40a5.up.railway.app)

## What it does

- Aggregates headlines from **BBC, NPR, The Guardian, Nikkei Asia, and SCMP**
- Uses **Google Gemini** to classify each story by topic, importance, and
  generate one-sentence editorial summaries
- Generates **"Today's Brief"** — 3 opinionated editorial framings of the
  day's most consequential stories, written like something a sharp
  friend would say at dinner
- **Political bias indicators** (AllSides-based) on every source
- **On-demand translation** (English → 中文 / 日本語) per article,
  cached to avoid repeat LLM spend
- **Trilingual UI** (English / 中文 / 日本語), with a first-visit nudge
  for non-English speakers
- **Click-to-copy talking points** — each must-read article gets 2 short
  conversational lines you can grab in one tap
- **24-hour rolling window** with SQLite persistence
- **Auto-refresh every 3 hours** (APScheduler) plus a manual refresh

## Tech stack

- **Backend**: Python 3.12, FastAPI, SQLite (WAL mode), APScheduler
- **AI**: Google Gemini 2.5 Flash — single batched call per refresh for
  cost efficiency; structured JSON output validated server-side
- **Frontend**: Vanilla JS, CSS custom properties, mobile-first responsive
- **Deployment**: Railway (auto-deploy from GitHub `main`)
- **Data sources**: BBC, NPR, The Guardian, Nikkei Asia, SCMP
  (parallel HTML scraping with BeautifulSoup)

## Architecture

The pipeline runs as a non-blocking background task — the API returns
immediately, the frontend polls for status, and articles stream in once
ready.

```
POST /api/refresh ──► background thread
                        │
                        ├─► fetch_all()       5 sources in parallel (ThreadPoolExecutor)
                        │                     → round-robin interleave + fuzzy dedup
                        │
                        ├─► existing_urls()   diff against SQLite to find new articles
                        │
                        ├─► fetch_og_images() 20-worker thumbnail fetch
                        │
                        ├─► analyze_batch()   ONE batched Gemini call:
                        │                     → topic + importance + summary + talking_points
                        │                     → per-article fallback on parse failure
                        │
                        ├─► save_articles()   INSERT OR IGNORE into SQLite
                        │
                        └─► generate_brief()  ONE more Gemini call:
                                              → 3 editorial framings from must-reads
                                              → URL validated against article set (no hallucinations)

GET  /api/news           ──► 24h rolling window, sorted by importance
GET  /api/brief          ──► cached editorial brief (in-memory)
GET  /api/refresh/status ──► state machine snapshot for frontend polling
POST /api/translate      ──► on-demand article translation (cached per url+lang)
```

**Design choices worth noting**:
- One Gemini call analyzes all ~50 headlines at once (cost + latency win
  vs per-article calls; fallback path remains for graceful degradation)
- Brief generation runs *synchronously* inside the refresh thread so
  it's ready exactly when the frontend polls `status=done`
- SQLite migrations happen idempotently on every startup via
  `ALTER TABLE ... IF NOT EXISTS`-style diffing
- All timestamps stored as UTC ISO strings with offset, so browsers in
  any timezone compute correct "5h ago" labels

## Setup

```bash
export GEMINI_API_KEY="your_key"
uv run uvicorn main:app --reload
```

Then open <http://localhost:8000>. Click **Pull latest** to fetch.

- **First refresh** scrapes 5 sources, fetches og:images concurrently,
  runs the batched Gemini analysis — typically under 30s.
- **Subsequent refreshes** are fast: URLs already in the DB skip both
  the image fetch and the Gemini call.

## Project structure

- `main.py` — FastAPI app: routes, refresh state machine, rate limiting,
  APScheduler integration, brief cache
- `fetcher.py` — per-source scrapers, og:image extraction, batched
  Gemini analysis, brief generation, translation
- `db.py` — SQLite layer (schema, idempotent migrations, JSON-encoded
  `talking_points`, 24h window queries)
- `static/index.html` — single-file vanilla-JS frontend
- `static/i18n.js` — UI translation dictionary + `t()` helper

## Deployment

The app is set up for Railway out of the box (`Procfile` + `railway.json`).
The same `Procfile` works on any Heroku-style platform; for Fly.io,
add a `fly.toml` pointing at the same start command.

**Required env vars**:

| Variable          | Required | Default     | Notes |
| ----------------- | -------- | ----------- | ----- |
| `GEMINI_API_KEY`  | yes      | —           | Get from <https://aistudio.google.com/apikey> |
| `DATABASE_PATH`   | no       | `./news.db` | Override when the platform mounts persistent storage at a fixed path (e.g. `/data/news.db` on Fly.io volumes). |
| `PORT`            | no       | `8000`      | Platforms set this at runtime. |

**Note on storage**: SQLite needs a persistent disk to survive restarts.
On platforms with ephemeral filesystems (default on Railway, Fly, Render
without a volume), `news.db` is wiped on every deploy / restart. For a
production deploy, attach a volume and point `DATABASE_PATH` at it.

## What I learned

- **Agent workflow orchestration** — designing a multi-step pipeline
  (parallel fetch → batch LLM analysis → structured output) that runs
  non-blocking and surfaces progress to the UI through polling.
- **Prompt engineering for structured output** — getting consistent JSON
  out of Gemini across ~50 articles in one shot, with anti-hallucination
  guards (URL whitelist validation, schema enforcement, BAD/GOOD example
  anchoring for tone).
- **FastAPI background tasks + polling pattern** — using a thread-safe
  state machine and a poll endpoint to give the user a live progress
  indicator without WebSockets or SSE.
- **SQLite schema design for a rolling cache** — designing migrations
  that run idempotently on every startup, using `INSERT OR IGNORE` for
  natural deduplication, and `PRAGMA journal_mode=WAL` for concurrent
  reads during writes.
- **Deploying a Python web app with persistent storage on Railway** —
  including healthcheck wiring, env-driven DB paths for volume mounts,
  and gotchas around static file caching.
- **Building a trilingual UI from day one** — i18n.js dictionary
  pattern with English fallback, locale-aware date formatting, and a
  first-visit nudge to surface language options to international users.

"""FastAPI app:serve frontend + /api/news + /api/refresh + /api/refresh/status.

Refresh 不再阻塞客户端:POST /api/refresh 立即返回,后台线程跑实际抓取,
前端轮询 /api/refresh/status 拿进度。
"""
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fetcher import fetch_all, analyze_batch, fetch_og_images, translate_article, generate_brief
from db import (
    init_db, existing_urls, save_articles,
    get_recent_articles, get_last_refreshed_at,
    get_article, set_translation,
)

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

init_db()

app = FastAPI(title="News Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ─── Brief cache ────────────────────────────────────────────────────────────
# In-memory; survives the refresh cycle but is lost on process restart.
# On startup we fire a background generation from existing DB articles.
_brief_lock = threading.Lock()
_brief_cache: dict = {"items": [], "generated_at": None}


def _get_brief_candidates():
    """Up to 10 must_read articles; pad to 6 with worth_knowing if needed."""
    all_articles = get_recent_articles(hours=24)
    must_reads = [a for a in all_articles if a.get("importance") == "must_read"][:10]
    candidates = list(must_reads)
    if len(candidates) < 6:
        worth = [a for a in all_articles if a.get("importance") == "worth_knowing"]
        candidates.extend(worth[: 6 - len(candidates)])
    return candidates


def _run_generate_brief():
    """Generate brief from current DB articles and update the in-memory cache."""
    try:
        candidates = _get_brief_candidates()
        if not candidates:
            print("[brief] no articles available yet", flush=True)
            return
        print(f"[brief] generating from {len(candidates)} articles…", flush=True)
        items = generate_brief(candidates)
        if items:
            with _brief_lock:
                _brief_cache["items"] = items
                _brief_cache["generated_at"] = datetime.now().isoformat(timespec="seconds")
            print(f"[brief] cached {len(items)} items", flush=True)
        else:
            print("[brief] generation returned no items", flush=True)
    except Exception as e:
        print(f"[brief] error: {e}", flush=True)


# ─── Refresh 状态机 ─────────────────────────────────────────────────────────
# 单进程内存态。多 worker 部署时每个进程各自一份,接受这个局限。
# 进程重启后 status 回到 idle,但 last_refreshed_at 走 DB 不会丢。
_state_lock = threading.Lock()
refresh_state = {
    "status": "idle",       # idle | running | done | error
    "started_at": None,     # ISO
    "finished_at": None,    # ISO
    "stats": None,          # {scraped, new, existing}
    "sources_ok": [],
    "sources_failed": [],
    "error": None,          # str
}


def _set_state(**kwargs):
    """带锁更新 refresh_state。"""
    with _state_lock:
        refresh_state.update(kwargs)


def _snapshot_state():
    with _state_lock:
        return dict(refresh_state)


def _run_refresh():
    """后台线程入口:抓取 → og:image → Gemini → 落 DB → 更新 state。"""
    try:
        headlines, statuses = fetch_all()

        sources_ok = [n for n, s in statuses.items() if s.startswith("OK")]
        sources_failed = [n for n, s in statuses.items() if s.startswith("FAILED")]

        seen = existing_urls([h["url"] for h in headlines])
        new_articles = [h for h in headlines if h["url"] not in seen]
        n_total, n_new = len(headlines), len(new_articles)
        n_existing = n_total - n_new

        print(f"Scraped {n_total} total headlines from sources", flush=True)
        print(f"Of which {n_new} are new URLs (not in DB)", flush=True)
        print(f"Of which {n_existing} already exist in DB", flush=True)
        if sources_failed:
            print(f"WARNING: sources failed: {sources_failed}", flush=True)

        if new_articles:
            print(f"Fetching og:image for {n_new} articles (20 workers)...", flush=True)
            images = fetch_og_images([a["url"] for a in new_articles])
            for a, img in zip(new_articles, images):
                a["og_image"] = img

            print(f"Analyzing {n_new} headlines (1 batched Gemini call)...", flush=True)
            analyses = analyze_batch(new_articles)
            for a, ana in zip(new_articles, analyses):
                a.update(ana)

            save_articles(new_articles)

        # Regenerate brief synchronously so it's ready when frontend polls "done"
        _run_generate_brief()

        _set_state(
            status="done",
            finished_at=datetime.now().isoformat(timespec="seconds"),
            stats={"scraped": n_total, "new": n_new, "existing": n_existing},
            sources_ok=sources_ok,
            sources_failed=sources_failed,
            error=None,
        )
    except Exception as e:
        # 包括 Gemini 整批 + 兜底都 fail、网络炸、DB 写挂等
        msg = f"{type(e).__name__}: {e}"
        print(f"ERROR: refresh failed — {msg}", flush=True)
        _set_state(
            status="error",
            finished_at=datetime.now().isoformat(timespec="seconds"),
            error=msg,
        )


# ─── 内存 rate limit:每个 endpoint 独立 bucket,共享一把锁 ─────────────────
_RATE_WINDOW = 60  # seconds
_REFRESH_LIMIT = 5       # POST /api/refresh
_TRANSLATE_LIMIT = 20    # POST /api/translate
_refresh_buckets: dict = defaultdict(deque)
_translate_buckets: dict = defaultdict(deque)
_rate_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    """Railway / 反代会走 X-Forwarded-For,优先取首个。"""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_check(ip: str, bucket: dict, limit: int):
    """返回 (allowed, wait_seconds)。命中限速时不入队,直接给等待秒数。"""
    now = time.time()
    with _rate_lock:
        q = bucket[ip]
        while q and q[0] < now - _RATE_WINDOW:
            q.popleft()
        if len(q) >= limit:
            wait = int(q[0] + _RATE_WINDOW - now) + 1
            return False, wait
        q.append(now)
        return True, 0


# ─── Startup ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def _startup():
    """Populate brief cache from existing DB articles (non-blocking background thread)."""
    threading.Thread(target=_run_generate_brief, daemon=True).start()


# ─── Routes ─────────────────────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/news")
def get_news():
    """返回 24h 窗口的文章 + 上次刷新时间(进程重启也能恢复)。"""
    articles = get_recent_articles(hours=24)
    snap = _snapshot_state()
    # last_refreshed:优先用 in-memory 的 finished_at,fall back to DB 里最新 fetched_at
    last_refreshed = snap["finished_at"] or get_last_refreshed_at()
    return {
        "articles": articles,
        "last_refreshed": last_refreshed,
        "total_count": len(articles),
    }


@app.post("/api/refresh")
def refresh(request: Request):
    """触发后台刷新。立即返回。"""
    ip = _client_ip(request)
    ok, wait = _rate_check(ip, _refresh_buckets, _REFRESH_LIMIT)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Too many refresh requests. Try again in {wait}s.",
                "retry_after": wait,
            },
        )

    with _state_lock:
        if refresh_state["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Refresh already running.",
                    "started_at": refresh_state["started_at"],
                },
            )
        # 重置状态,锁内一次性写好,避免半半态被读到
        refresh_state.update({
            "status": "running",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
            "stats": None,
            "sources_ok": [],
            "sources_failed": [],
            "error": None,
        })

    threading.Thread(target=_run_refresh, daemon=True).start()
    return {"status": "running", "started_at": refresh_state["started_at"]}


@app.get("/api/refresh/status")
def refresh_status():
    """前端轮询入口。返回当前 refresh_state 快照。"""
    return _snapshot_state()


# ─── /api/brief ─────────────────────────────────────────────────────────────
@app.get("/api/brief")
def get_brief():
    """Return the cached daily brief (3 items).  Empty list until first generation."""
    with _brief_lock:
        return dict(_brief_cache)


# ─── /api/translate ─────────────────────────────────────────────────────────
TRANSLATE_LANGS = {"zh", "ja"}


class TranslateRequest(BaseModel):
    article_id: str   # 即 article URL
    target_lang: str  # "zh" or "ja"


@app.post("/api/translate")
def translate_endpoint(body: TranslateRequest, request: Request):
    """按需翻译某条文章的标题+摘要。命中 DB 缓存就不调 Gemini。"""
    if body.target_lang not in TRANSLATE_LANGS:
        raise HTTPException(status_code=400, detail="invalid target_lang")

    ip = _client_ip(request)
    ok, wait = _rate_check(ip, _translate_buckets, _TRANSLATE_LIMIT)
    if not ok:
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Too many translation requests. Try again in {wait}s.",
                "retry_after": wait,
            },
        )

    article = get_article(body.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="article not found")

    # 命中缓存:不调 Gemini,直接吐
    cached_t = article.get(f"title_{body.target_lang}")
    cached_s = article.get(f"summary_{body.target_lang}")
    if cached_t and cached_s:
        return {"title_translated": cached_t, "summary_translated": cached_s, "cached": True}

    result = translate_article(
        article["title"], article.get("summary_en") or "", body.target_lang
    )
    if not result:
        raise HTTPException(status_code=502, detail="translation failed")

    title_t, summary_t = result
    set_translation(body.article_id, body.target_lang, title_t, summary_t)
    return {"title_translated": title_t, "summary_translated": summary_t, "cached": False}


# 直跑入口
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

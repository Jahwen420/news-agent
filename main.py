"""FastAPI app:serve frontend + /api/news 与 /api/refresh。

存储已经从 cache.json 迁到 SQLite (news.db),24h 滚动窗口。
跑起来:
    uv run uvicorn main:app --reload
"""
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fetcher import fetch_all, analyze_batch, fetch_og_images
from db import init_db, existing_urls, save_articles, get_recent_articles

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

# 启动时建表,幂等
init_db()

app = FastAPI(title="News Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/news")
def get_news():
    """直接吐 DB 里 24h 窗口的文章。"""
    articles = get_recent_articles(hours=24)
    return {
        "articles": articles,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/refresh")
def refresh():
    """抓 → 比对 DB 去重 → 仅对新文章拉 og:image + Gemini 分析 → 落 DB → 返回 24h 窗口。

    第二次刷新会快很多(大多数 URL 已在 DB,跳过 og:image 和 Gemini)。
    """
    try:
        headlines, statuses = fetch_all()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}")

    seen = existing_urls([h["url"] for h in headlines])
    new_articles = [h for h in headlines if h["url"] not in seen]
    n_total, n_new = len(headlines), len(new_articles)
    n_existing = n_total - n_new

    # 显式日志,便于诊断"为什么这次没新文章"
    print(f"Scraped {n_total} total headlines from sources", flush=True)
    print(f"Of which {n_new} are new URLs (not in DB)", flush=True)
    print(f"Of which {n_existing} already exist in DB", flush=True)
    print(f"Will analyze and save {n_new} new articles", flush=True)

    if new_articles:
        # 并发抓 og:image(10 workers, 5s/请求)
        print(f"Fetching og:image for {n_new} articles...", flush=True)
        images = fetch_og_images([a["url"] for a in new_articles])
        for a, img in zip(new_articles, images):
            a["og_image"] = img

        # 单次 Gemini 调用
        print(f"Analyzing {n_new} headlines (1 batched Gemini call)...", flush=True)
        analyses = analyze_batch(new_articles)
        for a, ana in zip(new_articles, analyses):
            a.update(ana)

        save_articles(new_articles)

    recent = get_recent_articles(hours=24)
    return {
        "articles": recent,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "sources_status": statuses,
        "stats": {
            "scraped": n_total,
            "new": n_new,
            "existing": n_existing,
        },
        "total_recent": len(recent),
    }

"""FastAPI app:serve frontend + 提供 /api/news 和 /api/refresh 两个端点。

跑起来:
    uv run uvicorn main:app --reload
然后访问 http://localhost:8000
"""
import json
import time
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fetcher import fetch_all, analyze

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
CACHE = ROOT / "cache.json"
EMPTY = {"articles": [], "updated_at": None, "sources_status": {}}

app = FastAPI(title="News Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# /static/* 用于未来的额外资源(图标、css 拆分等)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    """根路径返回 SPA 入口页。"""
    return FileResponse(STATIC / "index.html")


@app.get("/api/news")
def get_news():
    """读 cache.json 直接吐 JSON;没缓存就返回空骨架。"""
    if not CACHE.exists():
        return EMPTY
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # 缓存损坏不阻塞前端,返回空数据让用户重新 refresh
        return EMPTY


@app.post("/api/refresh")
def refresh():
    """触发抓取 + 分析,落盘到 cache.json,同步返回新数据。

    同步执行以便前端直接拿到结果;~15 条 × 7s sleep ≈ 2.5 分钟。
    后面要做后台异步可以改用 BackgroundTasks + 轮询状态。
    """
    try:
        headlines, statuses = fetch_all()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}")

    total = len(headlines)
    for i, item in enumerate(headlines, 1):
        if i > 1:
            time.sleep(7)  # Gemini 限速
        print(f"Analyzing {i}/{total}...", flush=True)
        item.update(analyze(item["title"]))

    data = {
        "articles": headlines,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "sources_status": statuses,
    }
    CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data

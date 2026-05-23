"""SQLite 持久层。表是 url-PRIMARY-KEY,INSERT OR IGNORE 实现"已见过的不重抓"。

24h 滚动窗口:文章保留在 DB 里(不主动清理),
get_recent_articles 在查询时过滤,只返回时间窗口内的。
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

# 部署平台常会把持久卷挂到固定路径(如 Fly.io 的 /data),用 DATABASE_PATH 覆盖。
# 本地不设环境变量则继续用项目根目录下的 news.db。
DB_PATH = Path(os.environ.get("DATABASE_PATH") or (Path(__file__).parent / "news.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url          TEXT PRIMARY KEY,
    title        TEXT,
    source       TEXT,
    published_at TEXT,           -- ISO string,可空
    fetched_at   TEXT NOT NULL,  -- ISO string,本机抓取时间
    summary_en   TEXT,
    topic        TEXT,
    importance   TEXT,
    og_image     TEXT
);
CREATE INDEX IF NOT EXISTS idx_fetched ON articles(fetched_at);
CREATE INDEX IF NOT EXISTS idx_published ON articles(published_at);
"""

# save 时填充缺省值,保证 named-param 插入不报 KeyError
_DEFAULTS = {
    "title": None, "source": None, "published_at": None,
    "summary_en": None, "topic": None, "importance": None, "og_image": None,
}


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """启动时调一次,幂等。会按需 mkdir 父目录(支持 /data/news.db 这种挂载路径)。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.executescript(SCHEMA)


def existing_urls(urls):
    """返回已经在 DB 里的 url 集合,用来挑出"新文章"。"""
    if not urls:
        return set()
    with _conn() as c:
        # SQLite 有 999 个 ? 上限,我们一次最多 50 条,够用
        placeholders = ",".join("?" * len(urls))
        rows = c.execute(
            f"SELECT url FROM articles WHERE url IN ({placeholders})", list(urls)
        ).fetchall()
        return {r["url"] for r in rows}


def _normalize_published(s):
    """把 NPR 的 '2026-05-22' 补成 '2026-05-22T00:00:00',让字符串比较仍然有序。"""
    if s and len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s + "T00:00:00"
    return s


def save_articles(articles):
    """UPSERT by url。已存在的 url 不更新(保留原 fetched_at 和已有分析结果)。"""
    if not articles:
        return
    now = datetime.now().isoformat(timespec="seconds")
    rows = []
    for a in articles:
        row = {**_DEFAULTS, **a}
        row["url"] = a["url"]
        row["fetched_at"] = row.get("fetched_at") or now
        row["published_at"] = _normalize_published(row.get("published_at"))
        rows.append(row)
    with _conn() as c:
        c.executemany(
            """INSERT OR IGNORE INTO articles
               (url, title, source, published_at, fetched_at,
                summary_en, topic, importance, og_image)
               VALUES (:url, :title, :source, :published_at, :fetched_at,
                       :summary_en, :topic, :importance, :og_image)""",
            rows,
        )


def get_recent_articles(hours=24):
    """文章窗口:我们在 hours 内抓到的,或 published_at 在窗口内的(后者补漏)。

    fetched_at 是主信号:DB 自己写的本机时间,格式统一可靠;published_at 来自
    各家网站,有 'YYYY-MM-DD' 也有 ISO,格式不稳。

    排序:must_read > worth_knowing > if_time,同级按时间新→旧。
    """
    threshold = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")
    with _conn() as c:
        rows = c.execute(
            """SELECT url, title, source, published_at, fetched_at,
                      summary_en, topic, importance, og_image
               FROM articles
               WHERE fetched_at >= ?
                  OR (published_at IS NOT NULL AND published_at >= ?)
               ORDER BY
                 CASE importance
                   WHEN 'must_read'     THEN 0
                   WHEN 'worth_knowing' THEN 1
                   ELSE 2
                 END,
                 COALESCE(published_at, fetched_at) DESC""",
            (threshold, threshold),
        ).fetchall()
        return [dict(r) for r in rows]

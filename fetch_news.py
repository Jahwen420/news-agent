"""多源新闻聚合:BBC + NPR + Guardian → 现代风格 HTML 输出。"""
import html
import re
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"}

# 用于过滤 NPR 节目名/栏目引导(它们经常长得像"Consider This from NPR")
NPR_NOISE = re.compile(r"\bfrom NPR\b|^Consider This\b|^Up First\b|^Morning Edition\b",
                       re.IGNORECASE)


def _get_soup(url: str) -> BeautifulSoup:
    """统一的 GET + 解析,带 UA 和超时。"""
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _clean(text: str) -> str:
    """用空格做 separator 后,折叠多余空白,避免相邻 span 拼成一坨字。"""
    return " ".join(text.split())


def _collect(soup, base_url, tag_names, source, noise_re=None):
    """通用提取:从指定 tag 取标题,向上找 <a> 取链接,做基础清洗与过滤。"""
    seen, items = set(), []
    for tag in soup.find_all(tag_names):
        # separator=" " 让 <span>Experience</span><span>...</span> 不会拼成 ExperienceWe...
        title = _clean(tag.get_text(separator=" ", strip=True))
        # 太短多半是导航/栏目名;命中噪音正则的跳过
        if not title or len(title) < 20 or title in seen:
            continue
        if noise_re and noise_re.search(title):
            continue
        a = tag.find_parent("a") or tag.find("a")
        href = a.get("href") if a else None
        url = urljoin(base_url, href) if href else base_url
        seen.add(title)
        items.append({"title": title, "url": url, "source": source})
    return items


def fetch_bbc():
    soup = _get_soup("https://www.bbc.com/news")
    return _collect(soup, "https://www.bbc.com", ["h2"], "BBC")


def fetch_npr():
    soup = _get_soup("https://www.npr.org/sections/news/")
    return _collect(soup, "https://www.npr.org", ["h2", "h3"], "NPR", NPR_NOISE)


def fetch_guardian():
    soup = _get_soup("https://www.theguardian.com/international")
    # Guardian 卡片标题主要在 <h3>;<h2> 多是 section 标题
    return _collect(soup, "https://www.theguardian.com", ["h3"], "Guardian")


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _similar(a: str, b: str, threshold: float = 0.85) -> bool:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio() >= threshold


def fetch_all():
    """三源并跑,记录状态,轮询交错合并,模糊去重,最多 15 条。"""
    sources = [("BBC", fetch_bbc), ("NPR", fetch_npr), ("Guardian", fetch_guardian)]
    statuses, per_source = {}, []
    for name, fn in sources:
        try:
            items = fn()
            statuses[name] = f"OK ({len(items)} headlines)"
            per_source.append(items)
        except Exception as e:
            statuses[name] = f"FAILED: {type(e).__name__}: {e}"
            per_source.append([])

    # 轮询交错,保证三源都有露出
    combined = []
    for i in range(max((len(s) for s in per_source), default=0)):
        for s in per_source:
            if i < len(s):
                combined.append(s[i])

    # 模糊去重
    deduped = []
    for item in combined:
        if any(_similar(item["title"], k["title"]) for k in deduped):
            continue
        deduped.append(item)
    return deduped[:15], statuses


# ─── HTML 模板 ────────────────────────────────────────────────────────────────
CSS = """
  :root {
    color-scheme: light dark;
    --bg: #f5f5f7;
    --card: #ffffff;
    --text: #1d1d1f;
    --muted: #6e6e73;
    --border: rgba(0, 0, 0, 0.06);
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 16px rgba(0, 0, 0, 0.04);
    --shadow-hover: 0 2px 4px rgba(0, 0, 0, 0.06), 0 12px 32px rgba(0, 0, 0, 0.08);
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f0f10;
      --card: #1c1c1e;
      --text: #f5f5f7;
      --muted: #98989d;
      --border: rgba(255, 255, 255, 0.08);
      --shadow: 0 1px 2px rgba(0, 0, 0, 0.3), 0 4px 16px rgba(0, 0, 0, 0.25);
      --shadow-hover: 0 2px 4px rgba(0, 0, 0, 0.35), 0 12px 32px rgba(0, 0, 0, 0.4);
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 Roboto, "Helvetica Neue", Arial, sans-serif;
    background: var(--bg); color: var(--text);
    -webkit-font-smoothing: antialiased;
    line-height: 1.5;
  }
  .wrap { max-width: 760px; margin: 0 auto; padding: 64px 24px 96px; }
  header {
    margin-bottom: 40px;
  }
  header h1 {
    font-size: 36px; font-weight: 700; letter-spacing: -0.02em;
    margin: 0 0 8px;
  }
  header .meta {
    font-size: 14px; color: var(--muted);
  }
  .feed { display: flex; flex-direction: column; gap: 12px; }
  article {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: var(--shadow);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }
  article:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
  }
  article a {
    color: inherit; text-decoration: none;
    display: block;
  }
  article a:hover .title { text-decoration: underline; text-decoration-thickness: 1px; }
  .title {
    font-size: 18px; font-weight: 600;
    margin-top: 10px;
    letter-spacing: -0.01em;
  }
  /* 来源徽章:浅色底 + 同色系深字,比纯色块更克制 */
  .badge {
    display: inline-block;
    padding: 3px 10px; border-radius: 999px;
    font-size: 11px; font-weight: 600;
    letter-spacing: 0.5px; text-transform: uppercase;
  }
  .badge.bbc      { background: rgba(187, 25, 25, 0.12);  color: #bb1919; }
  .badge.npr      { background: rgba(43, 108, 176, 0.12); color: #2b6cb0; }
  .badge.guardian { background: rgba(5, 41, 98, 0.14);    color: #052962; }
  @media (prefers-color-scheme: dark) {
    .badge.bbc      { background: rgba(255, 90, 90, 0.18);  color: #ff8a8a; }
    .badge.npr      { background: rgba(120, 180, 255, 0.18); color: #8ab8f0; }
    .badge.guardian { background: rgba(140, 180, 255, 0.18); color: #a8c3f0; }
  }
  footer {
    margin-top: 56px; text-align: center;
    color: var(--muted); font-size: 12px;
  }
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Today's Headlines</title>
  <style>{css}</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>Today's Headlines</h1>
      <div class="meta">{count} stories from BBC, NPR &amp; The Guardian &middot; {ts}</div>
    </header>
    <main class="feed">{items}</main>
    <footer>Generated by fetch_news.py</footer>
  </div>
</body>
</html>
"""


def render_card(item: dict) -> str:
    src = item["source"]
    return (
        f'<article>'
        f'<a href="{html.escape(item["url"], quote=True)}" target="_blank" rel="noopener">'
        f'<span class="badge {src.lower()}">{src}</span>'
        f'<div class="title">{html.escape(item["title"])}</div>'
        f'</a>'
        f'</article>'
    )


if __name__ == "__main__":
    headlines, statuses = fetch_all()

    # 终端先报告源状态
    print("Sources:")
    for name, status in statuses.items():
        print(f"  - {name}: {status}")
    print(f"After dedup, kept {len(headlines)} headlines.\n")

    for i, item in enumerate(headlines, 1):
        print(f"{i:2}. [{item['source']:8}] {item['title']}")

    items_html = "".join(render_card(h) for h in headlines)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = PAGE.format(css=CSS, items=items_html, ts=ts, count=len(headlines))
    with open("output.html", "w", encoding="utf-8") as f:
        f.write(page)

    print("\n✅ Saved to output.html")

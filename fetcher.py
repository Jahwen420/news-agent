"""新闻抓取 + Gemini 批量分析。被 main.py 的 FastAPI 路由调用。"""
import os
import re
import json
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from google import genai

GEMINI_MODEL = "gemini-2.5-flash"
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"}

NPR_NOISE = re.compile(r"\bfrom NPR\b|^Consider This\b|^Up First\b|^Morning Edition\b",
                       re.IGNORECASE)

TOPIC_ORDER = ["Geopolitics", "Business", "Tech", "China", "Japan", "Science", "Other"]
TOPICS = set(TOPIC_ORDER)
IMPORTANCE_ORDER = ["must_read", "worth_knowing", "if_time"]
IMPORTANCES = set(IMPORTANCE_ORDER)


# ─── 抓取 ────────────────────────────────────────────────────────────────────
def _get_soup(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _clean(text): return " ".join(text.split())


def _find_time(tag, max_depth=4):
    """从 tag 向上找最近祖先里第一个带 datetime 的 <time>。找不到返回 None。

    限制深度防止跨卡片串号(走太高会拿到隔壁卡片的时间)。
    """
    cur = tag.parent
    for _ in range(max_depth):
        if cur is None:
            return None
        t = cur.find("time", attrs={"datetime": True})
        if t and t.get("datetime"):
            return t.get("datetime")
        cur = cur.parent
    return None


def _collect(soup, base_url, tag_names, source, noise_re=None):
    """通用抽取:从指定 tag 取标题、链接、时间戳;统一清洗与去噪。"""
    seen, items = set(), []
    for tag in soup.find_all(tag_names):
        title = _clean(tag.get_text(separator=" ", strip=True))
        if not title or len(title) < 20 or title in seen:
            continue
        if noise_re and noise_re.search(title):
            continue
        a = tag.find_parent("a") or tag.find("a")
        href = a.get("href") if a else None
        url = urljoin(base_url, href) if href else base_url
        published_at = _find_time(tag)
        seen.add(title)
        items.append({
            "title": title, "url": url, "source": source,
            "published_at": published_at,
        })
    return items


def fetch_bbc():
    # BBC 列表页静态 HTML 里没 <time>,published_at 会全 null
    return _collect(_get_soup("https://www.bbc.com/news"),
                    "https://www.bbc.com", ["h2"], "BBC")


def fetch_npr():
    return _collect(_get_soup("https://www.npr.org/sections/news/"),
                    "https://www.npr.org", ["h2", "h3"], "NPR", NPR_NOISE)


def fetch_guardian():
    return _collect(_get_soup("https://www.theguardian.com/international"),
                    "https://www.theguardian.com", ["h3"], "Guardian")


def fetch_nikkei_asia():
    # Nikkei Asia 卡片标题主要在 <h2>;<time> 没 datetime 属性,时间会 null
    return _collect(_get_soup("https://asia.nikkei.com/"),
                    "https://asia.nikkei.com", ["h2"], "Nikkei Asia")


def fetch_scmp():
    # SCMP 用 h2(主推) + h3(次要列表)
    return _collect(_get_soup("https://www.scmp.com/"),
                    "https://www.scmp.com", ["h2", "h3"], "SCMP")


# ─── Open Graph 缩略图 ──────────────────────────────────────────────────────
def fetch_og_image(url, timeout=5):
    """请求文章页,从 <meta og:image> / <meta twitter:image> 拿封面 URL。

    失败一律返回 None,不抛错(在并发池里抛错会污染结果)。
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, "html.parser")
        for attrs in [{"property": "og:image"},
                      {"name": "twitter:image"},
                      {"property": "og:image:url"}]:
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                return tag["content"].strip()
    except Exception:
        pass
    return None


def fetch_og_images(urls, max_workers=20, timeout=5):
    """并发抓多个 URL 的 og:image。返回与输入等长的 list,失败位置为 None。

    20 个并发 + 5s 超时 → 50 条目标 <5s,实测一般 3-8s。
    """
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(lambda u: fetch_og_image(u, timeout), urls))


def _norm(s): return " ".join(s.lower().split())
def _similar(a, b, th=0.85): return SequenceMatcher(None, _norm(a), _norm(b)).ratio() >= th


def fetch_all():
    """跑五源 → 轮询交错 → 模糊去重 → 最多 50 条。返回 (articles, statuses)。"""
    sources = [
        ("BBC", fetch_bbc),
        ("NPR", fetch_npr),
        ("Guardian", fetch_guardian),
        ("Nikkei Asia", fetch_nikkei_asia),
        ("SCMP", fetch_scmp),
    ]
    statuses, per_source = {}, []
    for name, fn in sources:
        try:
            items = fn()
            statuses[name] = f"OK ({len(items)} headlines)"
            per_source.append(items)
        except Exception as e:
            statuses[name] = f"FAILED: {type(e).__name__}: {e}"
            per_source.append([])

    # 轮询交错:每源贡献 1 条,确保大源不会霸榜
    combined = []
    for i in range(max((len(s) for s in per_source), default=0)):
        for s in per_source:
            if i < len(s):
                combined.append(s[i])

    # 模糊去重(跨源同一事件)
    deduped = []
    for item in combined:
        if any(_similar(item["title"], k["title"]) for k in deduped):
            continue
        deduped.append(item)
    return deduped[:50], statuses


# ─── Gemini:批量分析 + 单条 fallback ────────────────────────────────────────
def _strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


FALLBACK_ANALYSIS = {
    "summary_en": "(Summary unavailable)",
    "topic": "Other",
    "importance": "if_time",
}

CRITERIA = """Topic criteria:
- Geopolitics: war, diplomacy, sanctions, government relations
- Business: markets, economy, major company news (non-tech)
- Tech: AI, software, hardware, tech companies
- China: anything centered on China (politics, economy, society)
- Japan: anything centered on Japan
- Science: climate, research, space, health science
- Other: sports, culture, crime, everything else

Importance criteria:
- must_read: major geopolitical event, market-moving news, things people will discuss at work tomorrow
- worth_knowing: notable but not urgent
- if_time: interesting but skippable"""


ANALYZE_PROMPT = f"""You are analyzing a news headline. Return ONLY a JSON object (no markdown, no other text) with these exact keys:
- "summary_en": one concise English sentence (max 25 words) explaining why this news matters — background context and significance
- "topic": one of [Geopolitics, Business, Tech, China, Japan, Science, Other]
- "importance": one of [must_read, worth_knowing, if_time]

{CRITERIA}

Headline: {{title}}
"""


BATCH_PROMPT = f"""You are analyzing {{n}} news headlines. Return ONLY a JSON array (no markdown, no other text) of exactly {{n}} objects, in the SAME ORDER as the headlines listed below. Each object must have these exact keys:
- "summary_en": one concise English sentence (max 25 words) explaining why this news matters
- "topic": one of [Geopolitics, Business, Tech, China, Japan, Science, Other]
- "importance": one of [must_read, worth_knowing, if_time]

{CRITERIA}

Headlines:
{{headlines}}
"""


def _validate_entry(entry):
    """把 Gemini 返回的单条对象规范化,无效字段走 fallback。"""
    if not isinstance(entry, dict):
        return dict(FALLBACK_ANALYSIS)
    topic = entry.get("topic") if entry.get("topic") in TOPICS else "Other"
    importance = entry.get("importance") if entry.get("importance") in IMPORTANCES else "if_time"
    summary = (entry.get("summary_en") or "").strip() or FALLBACK_ANALYSIS["summary_en"]
    return {"summary_en": summary, "topic": topic, "importance": importance}


def analyze(title):
    """单条调用 fallback,只在批量整体失败时被调。"""
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL, contents=ANALYZE_PROMPT.format(title=title)
        )
        data = json.loads(_strip_code_fence(resp.text or ""))
        return _validate_entry(data)
    except Exception:
        return dict(FALLBACK_ANALYSIS)


LANG_NAMES = {"zh": "Simplified Chinese", "ja": "Japanese"}


def translate_article(title, summary, target_lang):
    """单次 Gemini 调用,返回 (title_translated, summary_translated)。失败返回 None。"""
    lang_name = LANG_NAMES.get(target_lang)
    if not lang_name:
        return None
    prompt = (
        f"Translate the following news headline and summary into natural, "
        f"concise {lang_name}. Return ONLY a JSON object with keys "
        f"'title_translated' and 'summary_translated', no other text.\n\n"
        f"Headline: {title}\n"
        f"Summary: {summary}"
    )
    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        data = json.loads(_strip_code_fence(resp.text or ""))
        title_t = (data.get("title_translated") or "").strip()
        summary_t = (data.get("summary_translated") or "").strip()
        if not title_t or not summary_t:
            return None
        return title_t, summary_t
    except Exception as e:
        print(f"[translate_article] failed for {target_lang}: {e}", flush=True)
        return None


def analyze_batch(articles):
    """一次 Gemini 调用分析全部标题。

    - 成功:返回与 articles 等长的 list[dict],每项是 {summary_en, topic, importance}
    - 整批解析失败:逐条调 analyze() 兜底(慢但能完成)
    - 单条字段坏:用 _validate_entry 的 fallback 规范化
    """
    if not articles:
        return []
    headlines_block = "\n".join(f"{i+1}. {a['title']}" for i, a in enumerate(articles))
    prompt = BATCH_PROMPT.format(n=len(articles), headlines=headlines_block)
    try:
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        data = json.loads(_strip_code_fence(resp.text or ""))
        if not isinstance(data, list) or len(data) != len(articles):
            raise ValueError(f"expected list of {len(articles)}, got {type(data).__name__} len={len(data) if hasattr(data,'__len__') else '?'}")
        return [_validate_entry(e) for e in data]
    except Exception as e:
        print(f"[analyze_batch] batch failed ({e}); falling back to per-article calls", flush=True)
        return [analyze(a["title"]) for a in articles]

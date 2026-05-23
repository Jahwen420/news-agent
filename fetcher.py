"""新闻抓取 + Gemini 分析。被 main.py 的 FastAPI 路由调用,本身不做 IO 输出。"""
import os
import re
import json
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

# 主题/重要性白名单,用于校验 Gemini 返回
TOPIC_ORDER = ["Geopolitics", "Business", "Tech", "China", "Japan", "Science", "Other"]
TOPICS = set(TOPIC_ORDER)
IMPORTANCE_ORDER = ["must_read", "worth_knowing", "if_time"]
IMPORTANCES = set(IMPORTANCE_ORDER)


# ─── 抓取 ────────────────────────────────────────────────────────────────────
def _get_soup(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def _clean(text): return " ".join(text.split())


def _collect(soup, base_url, tag_names, source, noise_re=None):
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
        seen.add(title)
        items.append({"title": title, "url": url, "source": source})
    return items


def fetch_bbc():
    return _collect(_get_soup("https://www.bbc.com/news"),
                    "https://www.bbc.com", ["h2"], "BBC")


def fetch_npr():
    return _collect(_get_soup("https://www.npr.org/sections/news/"),
                    "https://www.npr.org", ["h2", "h3"], "NPR", NPR_NOISE)


def fetch_guardian():
    return _collect(_get_soup("https://www.theguardian.com/international"),
                    "https://www.theguardian.com", ["h3"], "Guardian")


def _norm(s): return " ".join(s.lower().split())
def _similar(a, b, th=0.85): return SequenceMatcher(None, _norm(a), _norm(b)).ratio() >= th


def fetch_all():
    """跑三源 → 轮询交错 → 模糊去重 → 最多 15 条。返回 (articles, statuses)。"""
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

    combined = []
    for i in range(max((len(s) for s in per_source), default=0)):
        for s in per_source:
            if i < len(s):
                combined.append(s[i])

    deduped = []
    for item in combined:
        if any(_similar(item["title"], k["title"]) for k in deduped):
            continue
        deduped.append(item)
    return deduped[:15], statuses


# ─── Gemini 摘要 + 分类 ──────────────────────────────────────────────────────
def _strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


ANALYZE_PROMPT = """You are analyzing a news headline. Return ONLY a JSON object (no markdown, no other text) with these exact keys:
- "summary_en": one concise English sentence (max 25 words) explaining why this news matters — background context and significance
- "topic": one of [Geopolitics, Business, Tech, China, Japan, Science, Other]
- "importance": one of [must_read, worth_knowing, if_time]

Topic criteria:
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
- if_time: interesting but skippable

Headline: {title}
"""


def analyze(title):
    """单次调用拿到 summary/topic/importance。解析失败时给保守默认。"""
    fallback = {"summary_en": "(Summary unavailable)", "topic": "Other", "importance": "if_time"}
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL, contents=ANALYZE_PROMPT.format(title=title)
        )
        data = json.loads(_strip_code_fence(resp.text or ""))
        topic = data.get("topic") if data.get("topic") in TOPICS else "Other"
        importance = data.get("importance") if data.get("importance") in IMPORTANCES else "if_time"
        summary = (data.get("summary_en") or "").strip() or fallback["summary_en"]
        return {"summary_en": summary, "topic": topic, "importance": importance}
    except Exception:
        return fallback

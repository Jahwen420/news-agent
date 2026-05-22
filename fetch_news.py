"""抓取 BBC News 首页标题并打印前 10 条,同时生成 HTML 文件。"""
import requests
from bs4 import BeautifulSoup

URL = "https://www.bbc.com/news"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"}


def fetch_headlines():
    """从 BBC 抓取所有 <h2> 标题,去重保序。"""
    resp = requests.get(URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    raw = [h.get_text(strip=True) for h in soup.find_all("h2")]
    return list(dict.fromkeys(t for t in raw if t))


if __name__ == "__main__":
    # 先调用函数,把结果存进 titles 变量
    titles = fetch_headlines()[:10]

    # 打印到终端
    for i, title in enumerate(titles, 1):
        print(f"{i:2}. {title}")

    # 生成 HTML 文件
    html = "<html><body><h1>Today's Headlines</h1><ol>"
    for title in titles:
        html += f"<li>{title}</li>"
    html += "</ol></body></html>"

    with open("output.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("\n✅ Saved to output.html")
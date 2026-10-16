# -*- coding: utf-8 -*-
"""采集白名单 RSS 要闻 -> data/news.json

分类：tech(科技) / finance(金融) / world(世界格局)
信源为白名单制，任何单个源失败不影响整体。
"""
import time

import feedparser
import requests

from common import CN_TZ, UA, dedupe, load_json, norm_title, now_cn, save_json

FEEDS = {
    "tech": [
        ("36氪", "https://36kr.com/feed"),
        ("虎嗅", "https://www.huxiu.com/rss/0.xml"),
        ("爱范儿", "https://www.ifanr.com/feed"),
        ("少数派", "https://sspai.com/feed"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ],
    "finance": [
        ("华尔街见闻", "https://wallstreetcn.com/rss"),
        ("FT中文网", "https://www.ftchinese.com/rss/feed"),
        ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ],
    "world": [
        ("BBC中文", "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"),
        ("卫报·世界", "https://www.theguardian.com/world/rss"),
    ],
}

MAX_PER_FEED = 8
MAX_TOTAL = 120


def fetch_feed(url: str, timeout: int = 20):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return feedparser.parse(r.content)


def entry_ts(e) -> float:
    t = e.get("published_parsed") or e.get("updated_parsed")
    return time.mktime(t) if t else 0.0


def build():
    items, failures = [], []
    for cat, feeds in FEEDS.items():
        for name, url in feeds:
            try:
                d = fetch_feed(url)
                for e in d.entries[:MAX_PER_FEED]:
                    title = (e.get("title") or "").strip()
                    link = e.get("link", "")
                    if not title or not link:
                        continue
                    items.append({
                        "title": title,
                        "url": link,
                        "source": name,
                        "category": cat,
                        "summary": (e.get("summary") or "")[:220],
                        "published": entry_ts(e),
                        "fetched_at": now_cn(),
                    })
            except Exception as ex:
                failures.append(f"{name}: {type(ex).__name__} {str(ex)[:100]}")

    items = dedupe(items, lambda x: norm_title(x["title"]))
    for it in items:
        it["published_cn"] = (
            time.strftime("%m-%d %H:%M", time.localtime(it["published"]))
            if it["published"]
            else ""
        )
    items.sort(key=lambda x: x["published"], reverse=True)
    out = {
        "updated_at": now_cn(),
        "categories": ["tech", "finance", "world"],
        "items": items[:MAX_TOTAL],
        "feed_failures": failures,
    }
    save_json("news.json", out)
    print(f"[news] {len(out['items'])} items; failures={failures or 'none'}")


if __name__ == "__main__":
    build()

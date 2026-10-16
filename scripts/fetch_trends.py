# -*- coding: utf-8 -*-
"""平台热度快照 -> data/trends.json

全自动信号源（v0）：
- appstore: App Store 美国区免费榜（官方 RSS JSON 接口）→ 新上榜/上升/下降
- bilibili: B 站全站热门榜（公开接口）→ 同上
- hn: Hacker News 首页热帖（Algolia 官方 API）
- reddit: Reddit r/all 当日热帖（公开 JSON）

X / TikTok / Instagram / Facebook / YouTube 无免费开放数据，由编辑精选兜底（editorial.json）。
"""
import requests

from common import UA, load_json, now_cn, save_json

APPSTORE = "https://itunes.apple.com/us/rss/topfreeapplications/limit=25/json"
BILI_RANK = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
BILI_POP = "https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1"
HN = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=20"
REDDIT = "https://www.reddit.com/r/all/top.json?t=day&limit=20"


def get(url: str, timeout: int = 25, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    r = requests.get(url, headers=h, timeout=timeout)
    r.raise_for_status()
    return r.json()


def compute_signals(items, prev_map):
    """prev_map: 名称 -> 上次排名。返回带 rank / signal / delta 的条目。"""
    for i, it in enumerate(items):
        rank = i + 1
        it["rank"] = rank
        pr = prev_map.get(it["name"])
        if pr is None:
            it["signal"] = "new"
            it["delta"] = None
        elif pr > rank:
            it["signal"] = "up"
            it["delta"] = pr - rank
        elif pr < rank:
            it["signal"] = "down"
            it["delta"] = rank - pr
        else:
            it["signal"] = "same"
            it["delta"] = 0
    return items


def prev_map_of(platform):
    """构造 名称->上次排名 映射；名称字段由各平台自定义。"""
    return {it["name"]: it["rank"] for it in platform.get("items", [])}


def safe_platform(key, name, fn):
    try:
        return {"name": name, "items": fn()}
    except Exception as ex:
        return {"name": name, "items": [], "error": f"{type(ex).__name__}: {str(ex)[:120]}"}


def build():
    prev = load_json("trends.json", {})
    prev_platforms = prev.get("platforms", {})
    out = {
        "updated_at": now_cn(),
        "platforms": {},
        "editorial": prev.get("editorial", {}),
    }

    def appstore():
        d = get(APPSTORE)
        items = []
        for e in d["feed"]["entry"]:
            items.append({
                "name": e["im:name"]["label"],
                "title": e["im:name"]["label"],
                "url": e["id"]["label"],
                "category": e["category"]["attributes"]["label"],
            })
        pm = prev_map_of(prev_platforms.get("appstore", {}))
        return compute_signals(items, pm)

    def _bili_get(url: str):
        r = requests.get(
            url,
            headers={
                "User-Agent": UA,
                "Referer": "https://www.bilibili.com/",
                "Origin": "https://www.bilibili.com",
            },
            timeout=20,
        )
        r.raise_for_status()
        d = r.json()
        if d.get("code", -1) != 0 or "data" not in d:
            raise RuntimeError(f"bili code={d.get('code')} msg={(d.get('message') or '')[:80]}")
        return d

    def bilibili():
        try:
            d = _bili_get(BILI_RANK)
        except Exception:
            d = _bili_get(BILI_POP)
        lst = d["data"]["list"]
        items = []
        for it in lst[:25]:
            items.append({
                "name": it["bvid"],
                "title": it["title"],
                "url": f"https://www.bilibili.com/video/{it['bvid']}",
                "author": it["owner"]["name"],
                "views": it["stat"]["view"],
            })
        pm = prev_map_of(prev_platforms.get("bilibili", {}))
        return compute_signals(items, pm)

    def hn():
        d = get(HN)
        items = []
        for i, it in enumerate(d["hits"]):
            items.append({
                "rank": i + 1,
                "title": it["title"],
                "url": it.get("url") or f"https://news.ycombinator.com/item?id={it['objectID']}",
                "discuss": f"https://news.ycombinator.com/item?id={it['objectID']}",
                "points": it.get("points", 0),
                "comments": it.get("num_comments", 0),
            })
        return items

    def reddit():
        d = get(REDDIT, headers={"User-Agent": UA})
        items = []
        for i, c in enumerate(d["data"]["children"][:20]):
            data = c["data"]
            items.append({
                "rank": i + 1,
                "title": data["title"],
                "sub": data["subreddit"],
                "url": "https://www.reddit.com" + data["permalink"],
                "score": data["score"],
            })
        return items

    out["platforms"]["appstore"] = safe_platform("appstore", "App Store 美国区免费榜", appstore)
    out["platforms"]["bilibili"] = safe_platform("bilibili", "Bilibili 全站热门榜", bilibili)
    out["platforms"]["hn"] = safe_platform("hn", "Hacker News 首页热帖", hn)
    out["platforms"]["reddit"] = safe_platform("reddit", "Reddit r/all 当日热帖", reddit)

    save_json("trends.json", out)
    print("[trends]", {k: len(v.get("items", [])) for k, v in out["platforms"].items()})


if __name__ == "__main__":
    build()

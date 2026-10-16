# -*- coding: utf-8 -*-
"""平台热度快照 -> data/trends.json

全自动信号源（v1）：
- appstore: App Store 美国区免费榜（官方 RSS JSON 接口）→ 新上榜/上升/下降
- bilibili: B 站全站热门榜（公开接口）→ 同上
- hn: Hacker News 首页热帖（Algolia 官方 API）
- reddit: Reddit r/all 当日热帖（公开 JSON）
- youtube: YouTube Trending 页面解析（ytInitialData）→ 尝试性自动源，失败则 error 降级

X / TikTok / Instagram / Facebook 无免费开放数据，由编辑精选兜底（social_trends.json，
模式 B，每日人工调研全球社交平台后写入）。
"""
import json
import re

import requests

from common import UA, load_json, now_cn, save_json

APPSTORE = "https://itunes.apple.com/us/rss/topfreeapplications/limit=25/json"
BILI_RANK = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
BILI_POP = "https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1"
HN = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=20"
REDDIT = "https://www.reddit.com/r/all/top.json?t=day&limit=20"
YOUTUBE_TRENDING = "https://www.youtube.com/feed/trending"


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

    def youtube():
        """YouTube Trending 页面解析（无官方免费 API，尽力而为，失败走 error 降级）。"""
        r = requests.get(
            YOUTUBE_TRENDING,
            headers={
                "User-Agent": UA,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=25,
        )
        r.raise_for_status()
        m = re.search(r"ytInitialData\s*=\s*(\{.+?\})\s*;", r.text, re.S)
        if not m:
            raise RuntimeError("ytInitialData not found")
        data = json.loads(m.group(1))

        def walk(node, out):
            if isinstance(node, dict):
                vr = node.get("videoRenderer")
                if isinstance(vr, dict):
                    out.append(vr)
                for v in node.values():
                    walk(v, out)
            elif isinstance(node, list):
                for v in node:
                    walk(v, out)

        found = []
        walk(data, found)
        items = []
        for vr in found[:25]:
            title = vr.get("title", {})
            text = None
            if isinstance(title, dict):
                runs = title.get("runs")
                if runs:
                    text = "".join(x.get("text", "") for x in runs)
                else:
                    text = title.get("simpleText")
            if not text:
                continue
            video_id = vr.get("videoId")
            owner = vr.get("ownerText", {}).get("runs") or []
            owner_name = owner[0].get("text", "") if owner else ""
            views = vr.get("viewCountText", {}).get("simpleText", "")
            pub = (vr.get("publishedTimeText", {}).get("simpleText", "")
                   or vr.get("publishedTimeText", {}).get("runs", [{}])[0].get("text", ""))
            items.append({
                "rank": len(items) + 1,
                "name": video_id,
                "title": text,
                "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else YOUTUBE_TRENDING,
                "channel": owner_name,
                "views": views,
                "published": pub,
            })
            if len(items) >= 25:
                break
        if not items:
            raise RuntimeError("no videoRenderer found")
        return items

    out["platforms"]["appstore"] = safe_platform("appstore", "App Store 美国区免费榜", appstore)
    out["platforms"]["bilibili"] = safe_platform("bilibili", "Bilibili 全站热门榜", bilibili)
    out["platforms"]["hn"] = safe_platform("hn", "Hacker News 首页热帖", hn)
    out["platforms"]["reddit"] = safe_platform("reddit", "Reddit r/all 当日热帖", reddit)
    out["platforms"]["youtube"] = safe_platform("youtube", "YouTube Trending（实验性自动源）", youtube)

    save_json("trends.json", out)
    print("[trends]", {k: len(v.get("items", [])) for k, v in out["platforms"].items()})


if __name__ == "__main__":
    build()

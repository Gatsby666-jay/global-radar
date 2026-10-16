# -*- coding: utf-8 -*-
"""GitHub 每周涨星榜（官方 Search API）+ 科技爱好者周刊 -> data/github.json / data/weekly.json

- 趋势榜：created >= 近7天，按 star 排序，体现「快速涨星的新项目」
- 周刊：优先解析阮一峰博客 RSS 拿到最新一期直达链接，仓库入口固定 github.com/ruanyf/weekly
"""
import os
import re
import time

import feedparser
import requests

from common import CN_TZ, UA, now_cn, save_json

GH_API = "https://api.github.com"
WEEKLY_REPO = "https://github.com/ruanyf/weekly"
RUANYIFENG_RSS = "http://www.ruanyifeng.com/blog/index.xml"


def gh_get(path, params=None, token=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "global-radar-bot"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(GH_API + path, params=params, headers=headers, timeout=25)
    r.raise_for_status()
    return r.json()


def fetch_trending(token=None, days: int = 7):
    from datetime import datetime, timedelta, timezone as tz

    since = (datetime.now(tz.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "q": f"created:>={since} stars:>50",
        "sort": "stars",
        "order": "desc",
        "per_page": 30,
    }
    data = gh_get("/search/repositories", params, token)
    repos = []
    for it in data.get("items", []):
        repos.append({
            "repo": it["full_name"],
            "url": it["html_url"],
            "desc": (it.get("description") or "")[:200],
            "lang": it.get("language") or "—",
            "stars": it.get("stargazers_count", 0),
            "forks": it.get("forks_count", 0),
            "created": (it.get("created_at") or "")[:10],
        })
    return repos


def fetch_weekly():
    w = {
        "number": None,
        "title": "科技爱好者周刊",
        "date": "",
        "url": WEEKLY_REPO,
        "issue_url": WEEKLY_REPO,
        "note": "",
        "updated_at": now_cn(),
    }
    # 方案 1：阮一峰博客 RSS
    try:
        r = requests.get(RUANYIFENG_RSS, headers={"User-Agent": UA}, timeout=20)
        d = feedparser.parse(r.content)
        for e in d.entries:
            m = re.search(r"科技爱好者周刊（第\s*(\d+)\s*期）", e.get("title", ""))
            if m:
                w["number"] = int(m.group(1))
                w["title"] = e.get("title", "").strip()
                w["issue_url"] = e.get("link", "") or WEEKLY_REPO
                t = e.get("published_parsed") or e.get("updated_parsed")
                w["date"] = time.strftime("%Y-%m-%d", t) if t else ""
                return w
        w["note"] = "RSS 中未找到最新一期标题，尝试 README 兜底"
    except Exception as ex:
        w["note"] = f"RSS 不可用（{type(ex).__name__}），尝试 README 兜底"

    # 方案 2：周刊仓库 README（GitHub 官方渠道）
    for url in (
        "https://raw.githubusercontent.com/ruanyf/weekly/master/README.md",
        "https://raw.githubusercontent.com/ruanyf/weekly/main/README.md",
    ):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            r.raise_for_status()
            text = r.text
            m = re.search(r"科技爱好者周刊（第\s*(\d+)\s*期）[^\n）]*）?", text)
            if m:
                w["number"] = int(re.search(r"第\s*(\d+)\s*期", m.group(0)).group(1))
                w["title"] = m.group(0).strip()[:80]
                line = text[m.start():text.find("\n", m.start())]
                link = re.search(r"\]\((https?://[^)]+)\)", line)
                w["issue_url"] = link.group(1) if link else WEEKLY_REPO
                w["date"] = ""
                w["note"] = "入口来自周刊仓库 README"
                return w
        except Exception:
            continue
    w["note"] = "RSS 与 README 均不可用，入口回退为仓库主页"
    return w


def build():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    try:
        repos = fetch_trending(token)
        note = ""
    except Exception as ex:
        repos = []
        note = f"{type(ex).__name__}: {str(ex)[:120]}"
    gh = {"updated_at": now_cn(), "window_days": 7, "repos": repos, "note": note}
    save_json("github.json", gh)
    weekly = fetch_weekly()
    save_json("weekly.json", weekly)
    print(f"[github] {len(repos)} repos; {note or 'ok'}")
    print(f"[weekly] {weekly['title']} -> {weekly['issue_url']}")


if __name__ == "__main__":
    build()

# -*- coding: utf-8 -*-
"""读取 data/*.json -> 渲染 templates -> 输出 site/（纯静态站点）。"""
import json
import os
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from common import DATA_DIR, ROOT, load_json, now_cn

SITE = os.path.join(ROOT, "site")
TEMPLATES = os.path.join(ROOT, "templates")
STATIC = os.path.join(ROOT, "static")

CAT_LABELS = {"tech": "科技", "finance": "金融", "world": "世界"}
SIGNAL_LABELS = {"new": "新上榜", "up": "上升", "down": "下降", "same": "持平"}
BASE_URL = os.environ.get(
    "BASE_URL", "https://<your-name>.github.io/global-radar/"
).rstrip("/")


def fmt_count(n):
    try:
        n = int(n)
    except Exception:
        return "—"
    if n >= 100000000:
        return f"{n / 100000000:.1f}亿"
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def fmt_delta(d):
    if d is None:
        return ""
    if d == 0:
        return "持平"
    return f"↑{d}" if d > 0 else f"↓{abs(d)}"


def build():
    news = load_json("news.json", {"items": []})
    github = load_json("github.json", {"repos": []})
    weekly = load_json("weekly.json", {})
    trends = load_json("trends.json", {"platforms": {}})
    editorial = load_json("editorial.json", {"title": "编辑精选", "summary": "", "items": []})

    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["fmt_count"] = fmt_count
    env.filters["fmt_delta"] = fmt_delta
    env.filters["signal_label"] = lambda s: SIGNAL_LABELS.get(s, "—")

    ctx = {
        "news": news,
        "github": github,
        "weekly": weekly,
        "trends": trends,
        "editorial": editorial,
        "cat_labels": CAT_LABELS,
        "built_at": now_cn(),
        "base_url": BASE_URL,
    }

    pages = [
        ("index.html", "index"),
        ("news.html", "news"),
        ("github.html", "github"),
        ("articles.html", "articles"),
        ("trends.html", "trends"),
    ]

    os.makedirs(SITE, exist_ok=True)
    for fname, page in pages:
        html = env.get_template(fname).render(page=page, **ctx)
        with open(os.path.join(SITE, fname), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[build] {fname}")

    shutil.copytree(STATIC, os.path.join(SITE, "static"), dirs_exist_ok=True)

    # sitemap
    sm_urls = [f"{BASE_URL}/{p}" if p != "index.html" else f"{BASE_URL}/"
               for p, _ in pages]
    with open(os.path.join(SITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in sm_urls:
            f.write(f"  <url><loc>{u}</loc></url>\n")
        f.write("</urlset>\n")
    print(f"[build] done -> {SITE}")


if __name__ == "__main__":
    build()

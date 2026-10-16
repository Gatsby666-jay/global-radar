# -*- coding: utf-8 -*-
"""共享工具：路径、UA、JSON 读写、文本归一化。"""
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

CN_TZ = timezone(timedelta(hours=8))


def now_cn() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S")


def data_path(name: str) -> str:
    return os.path.join(DATA_DIR, name)


def load_json(name: str, default=None):
    p = data_path(name)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(name: str, obj) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    p = data_path(name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return p


def norm_title(t) -> str:
    t = unicodedata.normalize("NFKC", t or "")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def dedupe(items, key_fn, limit=None):
    seen, out = set(), []
    for it in items:
        k = key_fn(it)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(it)
        if limit and len(out) >= limit:
            break
    return out

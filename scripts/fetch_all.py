# -*- coding: utf-8 -*-
"""一键采集入口：要闻 + GitHub 趋势/周刊 + 平台热度。"""
import fetch_github
import fetch_news
import fetch_trends
from common import now_cn


def main():
    print("== fetch_all start", now_cn())
    fetch_news.build()
    fetch_github.build()
    fetch_trends.build()
    print("== fetch_all done", now_cn())


if __name__ == "__main__":
    main()

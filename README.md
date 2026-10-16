# global-radar · 全球热点雷达

每日自动更新的全球科技 / 金融 / 世界格局要闻聚合站，附带 GitHub 每周涨星榜、科技爱好者周刊直达入口，以及全球流行内容与产品追踪（爆火追踪）。

- 部署：GitHub Pages（公开仓库，免费托管 + 免费自动化）
- 更新：GitHub Actions 定时任务，每天 3 次（北京时间 07:00 / 12:00 / 19:00）
- 技术：Python 采集 → Jinja2 静态生成 → GitHub Pages

## 页面

| 页面 | 内容 |
|---|---|
| 首页 index.html | 今日要闻 Top6、GitHub 涨星 Top6、周刊直达、平台热度 |
| 今日要闻 news.html | 科技 / 金融 / 世界 三类 RSS 聚合 |
| GitHub趋势 github.html | 近 7 天涨星最快新项目 Top30 + 科技爱好者周刊直达 |
| 前沿精选 articles.html | 编辑精选深度文章（每周更新） |
| 爆火追踪 trends.html | 全自动榜单（App Store / Bilibili / Hacker News / Reddit / YouTube） + 编辑追踪（X / TikTok / Instagram / Facebook / 视频风格观察） + 影响因子（名人效应 / 全球新闻 / 格局影响） |

## 数据来源

- 新闻：36氪、虎嗅、爱范儿、少数派、TechCrunch、The Verge、Ars Technica、华尔街见闻、FT中文网、CNBC、BBC中文、卫报（RSS，白名单制）
- GitHub 趋势：GitHub 官方 Search API（created >= 近7天，按 star 排序）
- 科技爱好者周刊：阮一峰博客 RSS + github.com/ruanyf/weekly
- 爆火追踪（自动）：App Store RSS（官方）、Bilibili 排行榜接口、Hacker News Algolia API、Reddit 公开 JSON、YouTube Trending（实验性：Invidious 公开实例 → 页面解析兜底）

> X / TikTok / Instagram / Facebook 无免费开放数据接口，由编辑每日调研全球公开信息后写入 `data/social_trends.json`（模式 B），
> 覆盖「哪些产品将爆火 / 不再流行、哪些视频风格正火、X 上哪些项目受关注」，并附名人效应 / 全球新闻 / 格局影响因子分析。

## 本地运行

```bash
pip install -r requirements.txt
python scripts/fetch_all.py   # 采集数据 -> data/*.json
python scripts/build.py       # 构建 -> site/
```

## 目录

```
.github/workflows/daily.yml   # 定时任务与部署
scripts/                      # 采集与构建脚本
templates/                    # Jinja2 页面模板
static/                       # 样式
data/                         # 每日数据快照（git 历史即数据库）
site/                         # 构建产物（由 CI 生成）
```

## 说明

本站仅聚合公开信息并做摘要，不转载全文，观点归原作者所有；AI 生成内容仅供参考。

"""
Trending Data Scraper Service for MoneyPrinterTurbo Pro

Scrapes hot topics from major Chinese platforms (Douyin, Bilibili, Weibo,
Zhihu, Baidu), provides trend analysis/scoring, keyword extraction, content
idea generation, and trend history tracking via SQLite.
"""

import json
import hashlib
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from collections import Counter

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class TrendItem:
    """A single trending topic from a platform."""
    platform: str
    rank: int
    title: str
    hot_score: int = 0
    url: str = ""
    category: str = ""
    description: str = ""
    fetched_at: str = ""

    @property
    def fingerprint(self) -> str:
        raw = f"{self.platform}:{self.title}"
        return hashlib.md5(raw.encode()).hexdigest()


@dataclass
class TrendAnalysis:
    """Aggregated analysis across platforms."""
    keyword: str
    frequency: int = 0
    platforms: list = field(default_factory=list)
    avg_rank: float = 0.0
    total_hot_score: int = 0
    composite_score: float = 0.0
    first_seen: str = ""
    last_seen: str = ""


@dataclass
class ContentIdea:
    """A generated content idea derived from trending data."""
    title: str
    hook: str
    outline: list = field(default_factory=list)
    tags: list = field(default_factory=list)
    source_trend: str = ""
    platform_affinity: str = ""
    estimated_engagement: str = "medium"


# ---------------------------------------------------------------------------
# Platform scrapers (public API endpoints, no auth required)
# ---------------------------------------------------------------------------

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
})
_TIMEOUT = 10


def _ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


def scrape_douyin(limit: int = 30) -> list[TrendItem]:
    """Scrape Douyin hot search list."""
    url = "https://www.douyin.com/aweme/v1/web/hot/search/list/"
    items: list[TrendItem] = []
    try:
        resp = _SESSION.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        word_list = data.get("word_list", [])
        for i, entry in enumerate(word_list[:limit]):
            items.append(TrendItem(
                platform="douyin",
                rank=i + 1,
                title=entry.get("word", ""),
                hot_score=int(entry.get("hot_value", 0)),
                url=f"https://www.douyin.com/search/{entry.get('word', '')}",
                fetched_at=_ts(),
            ))
    except Exception as exc:
        logger.warning("Douyin scrape failed: %s", exc)
    return items


def scrape_weibo(limit: int = 30) -> list[TrendItem]:
    """Scrape Weibo hot search (realtime)."""
    url = "https://weibo.com/ajax/side/hotSearch"
    items: list[TrendItem] = []
    try:
        resp = _SESSION.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        realtime = resp.json().get("data", {}).get("realtime", [])
        for i, entry in enumerate(realtime[:limit]):
            word = entry.get("word", "")
            items.append(TrendItem(
                platform="weibo",
                rank=i + 1,
                title=word,
                hot_score=int(entry.get("num", 0)),
                url=f"https://s.weibo.com/weibo?q=%23{word}%23",
                category=entry.get("category", ""),
                fetched_at=_ts(),
            ))
    except Exception as exc:
        logger.warning("Weibo scrape failed: %s", exc)
    return items


def scrape_bilibili(limit: int = 30) -> list[TrendItem]:
    """Scrape Bilibili hot search."""
    url = "https://app.bilibili.com/x/v2/search/trending/ranking"
    items: list[TrendItem] = []
    try:
        resp = _SESSION.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        trending = resp.json().get("data", {}).get("list", [])
        for i, entry in enumerate(trending[:limit]):
            keyword = entry.get("keyword", "") or entry.get("show_name", "")
            items.append(TrendItem(
                platform="bilibili",
                rank=i + 1,
                title=keyword,
                hot_score=int(entry.get("hot_id", 0)),
                url=f"https://search.bilibili.com/all?keyword={keyword}",
                fetched_at=_ts(),
            ))
    except Exception as exc:
        logger.warning("Bilibili scrape failed: %s", exc)
    return items


def scrape_zhihu(limit: int = 30) -> list[TrendItem]:
    """Scrape Zhihu hot list."""
    url = "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total"
    items: list[TrendItem] = []
    try:
        resp = _SESSION.get(url, timeout=_TIMEOUT, headers={
            "Referer": "https://www.zhihu.com/hot",
        })
        resp.raise_for_status()
        data = resp.json().get("data", [])
        for i, entry in enumerate(data[:limit]):
            target = entry.get("target", {})
            title = target.get("title", "")
            excerpt = target.get("excerpt", "")
            heat = int(entry.get("detail_text", "0").replace("万热度", "").replace(" 热度", "").strip() or 0)
            if "万" in entry.get("detail_text", ""):
                heat *= 10000
            items.append(TrendItem(
                platform="zhihu",
                rank=i + 1,
                title=title,
                hot_score=heat,
                url=f"https://www.zhihu.com/question/{target.get('id', '')}",
                description=excerpt,
                fetched_at=_ts(),
            ))
    except Exception as exc:
        logger.warning("Zhihu scrape failed: %s", exc)
    return items


def scrape_baidu(limit: int = 30) -> list[TrendItem]:
    """Scrape Baidu hot search."""
    url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
    items: list[TrendItem] = []
    try:
        resp = _SESSION.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        cards = resp.json().get("data", {}).get("cards", [])
        if cards:
            content_list = cards[0].get("content", [])
            for i, entry in enumerate(content_list[:limit]):
                items.append(TrendItem(
                    platform="baidu",
                    rank=i + 1,
                    title=entry.get("word", ""),
                    hot_score=int(entry.get("hotScore", 0)),
                    url=entry.get("url", ""),
                    description=entry.get("desc", ""),
                    fetched_at=_ts(),
                ))
    except Exception as exc:
        logger.warning("Baidu scrape failed: %s", exc)
    return items


# Platform registry
PLATFORM_SCRAPERS = {
    "douyin": scrape_douyin,
    "weibo": scrape_weibo,
    "bilibili": scrape_bilibili,
    "zhihu": scrape_zhihu,
    "baidu": scrape_baidu,
}


# ---------------------------------------------------------------------------
# SQLite history store
# ---------------------------------------------------------------------------

class TrendHistoryStore:
    """Persists trend snapshots to a local SQLite database."""

    _DDL = """
    CREATE TABLE IF NOT EXISTS trend_snapshots (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        fingerprint TEXT NOT NULL,
        platform    TEXT NOT NULL,
        rank        INTEGER,
        title       TEXT NOT NULL,
        hot_score   INTEGER DEFAULT 0,
        url         TEXT DEFAULT '',
        category    TEXT DEFAULT '',
        description TEXT DEFAULT '',
        fetched_at  TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ts_fingerprint ON trend_snapshots(fingerprint);
    CREATE INDEX IF NOT EXISTS idx_ts_platform    ON trend_snapshots(platform);
    CREATE INDEX IF NOT EXISTS idx_ts_fetched_at  ON trend_snapshots(fetched_at);

    CREATE TABLE IF NOT EXISTS trend_keywords (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword    TEXT NOT NULL,
        frequency  INTEGER DEFAULT 1,
        platforms  TEXT DEFAULT '[]',
        first_seen TEXT,
        last_seen  TEXT,
        UNIQUE(keyword)
    );
    """

    def __init__(self, db_path: str = "trending_history.db"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self._DDL)

    # -- persistence --

    def save_snapshot(self, items: list[TrendItem]) -> int:
        rows = [
            (it.fingerprint, it.platform, it.rank, it.title,
             it.hot_score, it.url, it.category, it.description, it.fetched_at)
            for it in items
        ]
        self._conn.executemany(
            "INSERT INTO trend_snapshots "
            "(fingerprint, platform, rank, title, hot_score, url, category, description, fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        self._conn.commit()
        return len(rows)

    def upsert_keyword(self, keyword: str, platform: str, hot_score: int):
        now = _ts()
        existing = self._conn.execute(
            "SELECT * FROM trend_keywords WHERE keyword = ?", (keyword,)
        ).fetchone()
        if existing:
            platforms = json.loads(existing["platforms"])
            if platform not in platforms:
                platforms.append(platform)
            self._conn.execute(
                "UPDATE trend_keywords SET frequency=frequency+1, "
                "platforms=?, last_seen=? WHERE keyword=?",
                (json.dumps(platforms), now, keyword),
            )
        else:
            self._conn.execute(
                "INSERT INTO trend_keywords (keyword, frequency, platforms, first_seen, last_seen) "
                "VALUES (?,?,?,?,?)",
                (keyword, 1, json.dumps([platform]), now, now),
            )
        self._conn.commit()

    def get_keyword_history(self, keyword: str, days: int = 30) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._conn.execute(
            "SELECT * FROM trend_snapshots WHERE title LIKE ? AND fetched_at >= ? ORDER BY fetched_at",
            (f"%{keyword}%", cutoff),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_top_keywords(self, limit: int = 50, days: int = 7) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._conn.execute(
            "SELECT keyword, frequency, platforms, first_seen, last_seen "
            "FROM trend_keywords WHERE last_seen >= ? ORDER BY frequency DESC LIMIT ?",
            (cutoff, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self._conn.close()


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

# Common Chinese stop words (compact set)
_STOP_WORDS = frozenset(
    "的 了 在 是 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 "
    "看 好 自己 这 他 她 它 们 那 什么 怎么 如何 可以 被 把 让 给 从 而 但 而且 或 "
    "如果 因为 所以 虽然 这个 那个 之 与 及 等 吧 吗 呢 啊 哦 嗯 对 于 中 为".split()
)


def extract_keywords(titles: list[str], top_n: int = 20) -> list[tuple[str, int]]:
    """Simple jieba-free keyword extraction using regex tokenisation + frequency."""
    # Try jieba first; fall back to regex-based extraction
    try:
        import jieba  # type: ignore
        tokens: list[str] = []
        for t in titles:
            tokens.extend(w for w in jieba.cut(t) if len(w) > 1 and w not in _STOP_WORDS)
    except ImportError:
        # Regex: extract Chinese character runs (2+ chars) and alphanumeric words
        tokens = []
        for t in titles:
            cn_parts = re.findall(r"[\u4e00-\u9fff]{2,}", t)
            en_parts = re.findall(r"[a-zA-Z0-9]{2,}", t)
            tokens.extend(p for p in cn_parts if p not in _STOP_WORDS)
            tokens.extend(en_parts)

    counter = Counter(tokens)
    return counter.most_common(top_n)


# ---------------------------------------------------------------------------
# Trend analysis & scoring
# ---------------------------------------------------------------------------

def analyse_trends(all_items: list[TrendItem]) -> list[TrendAnalysis]:
    """Group items by title keyword and compute composite scores."""
    groups: dict[str, list[TrendItem]] = {}
    for item in all_items:
        key = item.title.strip()
        if not key:
            continue
        groups.setdefault(key, []).append(item)

    analyses: list[TrendAnalysis] = []
    for keyword, items in groups.items():
        platforms = list({it.platform for it in items})
        avg_rank = sum(it.rank for it in items) / len(items)
        total_hot = sum(it.hot_score for it in items)
        # Composite: boost multi-platform presence, penalise low rank
        platform_bonus = len(platforms) * 150
        rank_factor = max(0, 100 - avg_rank * 2)
        composite = total_hot + platform_bonus + rank_factor * 100
        fetched_times = [it.fetched_at for it in items if it.fetched_at]
        analyses.append(TrendAnalysis(
            keyword=keyword,
            frequency=len(items),
            platforms=platforms,
            avg_rank=round(avg_rank, 2),
            total_hot_score=total_hot,
            composite_score=composite,
            first_seen=min(fetched_times) if fetched_times else "",
            last_seen=max(fetched_times) if fetched_times else "",
        ))

    analyses.sort(key=lambda a: a.composite_score, reverse=True)
    return analyses


# ---------------------------------------------------------------------------
# Content idea generation
# ---------------------------------------------------------------------------

# Template hooks for different content angles
_HOOK_TEMPLATES = [
    "你不知道的{topic}真相，看完震惊了！",
    "{topic}背后的秘密，99%的人都不知道",
    "深度解析：{topic}到底意味着什么？",
    "一分钟带你了解{topic}的前因后果",
    "从{topic}看中国互联网最新趋势",
    "为什么{topic}突然火了？背后原因让人深思",
    "{topic}全网最全解读，建议收藏！",
    "当{topic}遇上短视频，会碰撞出什么火花？",
]

_OUTLINE_TEMPLATES = [
    ["背景介绍：什么是{topic}", "核心看点分析", "用户热议焦点", "总结与个人观点"],
    ["热点事件回顾", "多方观点对比", "深层原因剖析", "未来趋势预判"],
    ["开篇抛出悬念", "逐步揭秘真相", "数据和案例佐证", "引导互动讨论"],
]


def generate_content_ideas(
    analyses: list[TrendAnalysis],
    limit: int = 10,
) -> list[ContentIdea]:
    """Generate short-video content ideas from trend analyses."""
    import random
    ideas: list[ContentIdea] = []
    for ta in analyses[:limit]:
        topic = ta.keyword
        hook_tmpl = random.choice(_HOOK_TEMPLATES)
        outline_tmpl = random.choice(_OUTLINE_TEMPLATES)
        engagement = "high" if ta.composite_score > 50000 else (
            "medium" if ta.composite_score > 10000 else "low"
        )
        pref_platform = ta.platforms[0] if ta.platforms else "douyin"
        ideas.append(ContentIdea(
            title=f"🔥 热点解读：{topic}",
            hook=hook_tmpl.format(topic=topic),
            outline=[s.format(topic=topic) for s in outline_tmpl],
            tags=[topic, "热点", "解读", pref_platform],
            source_trend=topic,
            platform_affinity=pref_platform,
            estimated_engagement=engagement,
        ))
    return ideas


# ---------------------------------------------------------------------------
# Main service facade
# ---------------------------------------------------------------------------

class TrendingService:
    """
    High-level service for scraping, analysing, and persisting trending data.

    Usage:
        svc = TrendingService(db_path="trends.db")
        items = svc.fetch_all(limit=20)
        top = svc.analyse(top_n=10)
        ideas = svc.ideas(count=5)
        history = svc.keyword_history("AI", days=14)
    """

    def __init__(self, db_path: str = "trending_history.db"):
        self._store = TrendHistoryStore(db_path)
        self._last_items: list[TrendItem] = []
        self._last_analyses: list[TrendAnalysis] = []

    # -- public API --

    def fetch_platform(self, platform: str, limit: int = 30) -> list[TrendItem]:
        """Fetch trending items from a single platform."""
        scraper = PLATFORM_SCRAPERS.get(platform)
        if not scraper:
            raise ValueError(f"Unknown platform: {platform}. Choose from {list(PLATFORM_SCRAPERS)}")
        items = scraper(limit=limit)
        if items:
            self._store.save_snapshot(items)
            for it in items:
                self._store.upsert_keyword(it.title, it.platform, it.hot_score)
        return items

    def fetch_all(
        self,
        platforms: Optional[list[str]] = None,
        limit: int = 30,
    ) -> list[TrendItem]:
        """Fetch from all (or selected) platforms and persist."""
        targets = platforms or list(PLATFORM_SCRAPERS)
        all_items: list[TrendItem] = []
        for plat in targets:
            logger.info("Fetching trends from %s ...", plat)
            try:
                items = self.fetch_platform(plat, limit=limit)
                all_items.extend(items)
                logger.info("  -> %d items from %s", len(items), plat)
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", plat, exc)
        self._last_items = all_items
        return all_items

    def analyse(self, items: Optional[list[TrendItem]] = None, top_n: int = 20) -> list[TrendAnalysis]:
        """Run cross-platform analysis and return top trends."""
        target = items or self._last_items
        if not target:
            logger.warning("No items to analyse. Call fetch_all() first.")
            return []
        self._last_analyses = analyse_trends(target)
        return self._last_analyses[:top_n]

    def extract_keywords(self, items: Optional[list[TrendItem]] = None, top_n: int = 20) -> list[tuple[str, int]]:
        """Extract hot keywords from trend titles."""
        target = items or self._last_items
        titles = [it.title for it in target if it.title]
        return extract_keywords(titles, top_n=top_n)

    def ideas(self, count: int = 10, analyses: Optional[list[TrendAnalysis]] = None) -> list[ContentIdea]:
        """Generate content ideas from analysed trends."""
        target = analyses or self._last_analyses
        if not target:
            logger.warning("No analyses available. Call analyse() first.")
            return []
        return generate_content_ideas(target, limit=count)

    def keyword_history(self, keyword: str, days: int = 30) -> list[dict]:
        """Retrieve historical snapshots for a keyword."""
        return self._store.get_keyword_history(keyword, days=days)

    def top_keywords(self, limit: int = 50, days: int = 7) -> list[dict]:
        """Get most frequently trending keywords."""
        return self._store.get_top_keywords(limit=limit, days=days)

    def platform_summary(self, items: Optional[list[TrendItem]] = None) -> dict[str, int]:
        """Count items per platform."""
        target = items or self._last_items
        counter: Counter = Counter(it.platform for it in target)
        return dict(counter)

    def close(self):
        self._store.close()

    # -- context manager --

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ---------------------------------------------------------------------------
# CLI helper (quick test)
# ---------------------------------------------------------------------------

def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Trending scraper CLI")
    parser.add_argument("--platforms", nargs="*", default=None,
                        help="Platforms to scrape (default: all)")
    parser.add_argument("--limit", type=int, default=10, help="Items per platform")
    parser.add_argument("--db", default="trending_history.db", help="SQLite DB path")
    parser.add_argument("--ideas", type=int, default=5, help="Generate N content ideas")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with TrendingService(db_path=args.db) as svc:
        items = svc.fetch_all(platforms=args.platforms, limit=args.limit)
        print(f"\n📊 Fetched {len(items)} trending items total\n")

        analyses = svc.analyse(top_n=10)
        print("🏆 Top Trends (composite score):")
        for i, ta in enumerate(analyses, 1):
            print(f"  {i}. [{ta.keyword}] score={ta.composite_score:.0f} "
                  f"platforms={ta.platforms} rank_avg={ta.avg_rank}")

        kw = svc.extract_keywords(top_n=15)
        print("\n🔑 Hot Keywords:")
        for word, freq in kw:
            print(f"  {word}: {freq}")

        if args.ideas > 0:
            ideas = svc.ideas(count=args.ideas)
            print(f"\n💡 Content Ideas ({len(ideas)}):")
            for idea in ideas:
                print(f"  📌 {idea.title}")
                print(f"     Hook: {idea.hook}")
                print(f"     Tags: {', '.join(idea.tags)}")
                print()


if __name__ == "__main__":
    _main()

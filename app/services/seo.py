"""
SEO Optimizer Service for MoneyPrinterTurbo Pro.

Provides viral title generation, meta description generation,
hashtag/tag generation for multiple platforms, and keyword density analysis.
"""

import re
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Platform(Enum):
    """Supported social media / video platforms."""
    DOUYIN = "douyin"
    BILIBILI = "bilibili"
    XIAOHONGSHU = "xiaohongshu"
    YOUTUBE = "youtube"


@dataclass
class SEOAnalysis:
    """Container for full SEO analysis results."""
    titles: List[str] = field(default_factory=list)
    descriptions: List[str] = field(default_factory=list)
    hashtags: Dict[str, List[str]] = field(default_factory=dict)
    keyword_density: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class SEOOptimizer:
    """
    All-in-one SEO optimizer for short-form and long-form video content.

    Features:
    - Viral title generation using proven copywriting formulas
    - Meta / description generation with CTAs
    - Platform-specific hashtag and tag generation
    - Keyword density analysis with actionable feedback
    """

    # ── title formula templates ──────────────────────────────────────────

    _NUMBER_ADJECTIVE_TEMPLATES = [
        "{count} {adj} {keyword} You Need to See in {year}",
        "{count} {adj} Ways to {verb} {keyword}",
        "{count} {adj} {keyword} Tips That Actually Work",
        "{count} {adj} {keyword} Secrets Experts Won't Tell You",
        "{count} {adj} {keyword} Ideas for {year}",
        "{count} {adj} {keyword} Hacks That Changed My Life",
    ]

    _QUESTION_TEMPLATES = [
        "Is {keyword} Worth It in {year}? (Honest Review)",
        "Why Is {keyword} So Popular Right Now?",
        "What Happens When You {verb} {keyword}?",
        "Can {keyword} Really {benefit}?",
        "How Do You {verb} {keyword} Like a Pro?",
        "Do You Make These {keyword} Mistakes?",
    ]

    _HOW_TO_TEMPLATES = [
        "How to {verb} {keyword} in {minutes} Minutes",
        "How to {verb} {keyword} (Step-by-Step Guide)",
        "How I {past_verb} {keyword} — And You Can Too",
        "How to {verb} {keyword} on a Budget",
        "How to {verb} {keyword} Even If You're a Beginner",
    ]

    _EMOTIONAL_TEMPLATES = [
        "I Tried {keyword} for 30 Days — Here's What Happened",
        "This {keyword} {item} Changed Everything",
        "Stop {bad_verb} {keyword} — Do THIS Instead",
        "The {keyword} {item} Nobody Talks About",
        "Warning: Don't {verb} {keyword} Until You Watch This",
        "I Can't Believe This {keyword} {item} Exists!",
    ]

    _LISTICLE_TEMPLATES = [
        "Top {count} {keyword} for {audience} in {year}",
        "The Ultimate {keyword} Checklist ({count} Items)",
        "{count} {keyword} Trends You Can't Ignore in {year}",
        "{count} Reasons {keyword} Is Taking Over {year}",
        "Best {keyword} Ranked — {year} Edition",
    ]

    # ── platform tag pools ───────────────────────────────────────────────

    _PLATFORM_TAG_POOLS: Dict[str, List[str]] = {
        Platform.DOUYIN.value: [
            "热门", "推荐", "抖音", "日常", "生活", "教程", "干货",
            "涨知识", "实用", "分享", "技巧", "必看", "爆款", "精选",
            "种草", "好物推荐", "生活小妙招", "每日分享",
        ],
        Platform.BILIBILI.value: [
            "bilibili", "知识", "科普", "教程", "干货分享", "学习",
            "日常", "生活", "技术", "教程分享", "成长", "实用",
            "B站", "up主", "新人up", "必看", "推荐",
        ],
        Platform.XIAOHONGSHU.value: [
            "小红书", "种草", "好物", "分享", "日常", "干货",
            "合集", "推荐", "实用", "生活", "技巧", "变美",
            "攻略", "测评", "真实分享", "沉浸式", "氛围感",
        ],
        Platform.YOUTUBE.value: [
            "tutorial", "howto", "tips", "review", "guide", "explained",
            "vlog", "daily", "shorts", "trending", "mustwatch",
            "education", "tech", "lifehack", "top10", "beginner",
        ],
    }

    # ── common adjectives / power words ─────────────────────────────────

    _ADJECTIVES = [
        "Amazing", "Incredible", "Essential", "Powerful", "Insane",
        "Secret", "Proven", "Epic", "Mind-Blowing", "Genius",
        "Unbelievable", "Shocking", "Brilliant", "Ultimate", "Simple",
    ]

    _POWER_VERBS = [
        "Master", "Boost", "Transform", "Dominate", "Unlock",
        "Crush", "Accelerate", "Supercharge", "Level Up", "Nail",
        "Hack", "Skyrocket", "Maximize", "Discover", "Conquer",
    ]

    _BENEFITS = [
        "Save You Money", "Change Your Life", "Make You Smarter",
        "Boost Your Productivity", "Help You Grow", "Go Viral",
        "Get You Results", "Save You Time", "Work Every Time",
    ]

    _BAD_VERBS = [
        "Wasting Money on", "Ignoring", "Buying", "Using", "Overlooking",
    ]

    _ITEMS = [
        "Trick", "Method", "Tool", "Secret", "Strategy", "Technique",
        "Hack", "Approach", "Discovery",
    ]

    _AUDIENCES = [
        "Beginners", "Professionals", "Students", "Everyone",
        "Creators", "Entrepreneurs", "Parents", "Freelancers",
    ]

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract meaningful keywords from raw text, removing stop words."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "and",
            "but", "or", "nor", "not", "so", "yet", "both", "either",
            "neither", "each", "every", "all", "any", "few", "more",
            "most", "other", "some", "such", "no", "only", "own", "same",
            "than", "too", "very", "just", "because", "if", "when",
            "while", "this", "that", "these", "those", "it", "its",
            "i", "me", "my", "we", "our", "you", "your", "he", "him",
            "his", "she", "her", "they", "them", "their",
        }
        words = re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower())
        return [w for w in words if w not in stop_words and len(w) > 1]

    @staticmethod
    def _count_words(text: str) -> List[str]:
        """Return all word tokens (case-folded) from text."""
        return re.findall(r"[a-zA-Z\u4e00-\u9fff]+", text.lower())

    # ── title generation ─────────────────────────────────────────────────

    def generate_titles(
        self,
        keyword: str,
        *,
        count: int = 10,
        language: str = "en",
        year: Optional[int] = None,
    ) -> List[str]:
        """
        Generate viral title ideas using multiple copywriting formulas.

        Args:
            keyword: The primary topic / keyword.
            count: How many titles to return (distributed across formulas).
            language: 'en' or 'zh'.
            year: Year to embed (defaults to current year via import).

        Returns:
            List of title strings.
        """
        if year is None:
            from datetime import datetime
            year = datetime.now().year

        verb = random.choice(self._POWER_VERBS)
        adj = random.choice(self._ADJECTIVES)
        benefit = random.choice(self._BENEFITS)
        bad_verb = random.choice(self._BAD_VERBS)
        item = random.choice(self._ITEMS)
        audience = random.choice(self._AUDIENCES)
        minutes = random.choice(["5", "10", "15", "20", "30"])
        past_verb = verb + ("d" if not verb.endswith("e") else "d")

        context = dict(
            count=str(random.randint(3, 15)),
            adj=adj,
            keyword=keyword,
            year=str(year),
            verb=verb,
            benefit=benefit,
            bad_verb=bad_verb,
            item=item,
            audience=audience,
            minutes=minutes,
            past_verb=past_verb,
        )

        all_templates = (
            self._NUMBER_ADJECTIVE_TEMPLATES
            + self._QUESTION_TEMPLATES
            + self._HOW_TO_TEMPLATES
            + self._EMOTIONAL_TEMPLATES
            + self._LISTICLE_TEMPLATES
        )
        random.shuffle(all_templates)

        results: List[str] = []
        for tpl in all_templates:
            if len(results) >= count:
                break
            try:
                title = tpl.format(**context)
            except (KeyError, IndexError):
                continue
            results.append(title)

        # If we still need more, do generic fills
        generic_fills = [
            f"{keyword} — Everything You Need to Know ({year})",
            f"The Best {keyword} Guide for {year}",
            f"{keyword}: A Complete Beginner's Walkthrough",
            f"Why {keyword} Is the Future (And What You Should Do)",
            f"{keyword} Deep Dive — What Nobody Tells You",
        ]
        for title in generic_fills:
            if len(results) >= count:
                break
            results.append(title)

        return results[:count]

    # ── meta description ─────────────────────────────────────────────────

    def generate_descriptions(
        self,
        keyword: str,
        *,
        count: int = 3,
        max_length: int = 160,
        include_cta: bool = True,
    ) -> List[str]:
        """
        Generate SEO-friendly meta descriptions.

        Args:
            keyword: Primary keyword.
            count: Number of description variants.
            max_length: Character limit (Google ~160).
            include_cta: Whether to append a call-to-action.

        Returns:
            List of description strings.
        """
        ctas = [
            "Watch now to learn more!",
            "Don't miss out — hit play!",
            "Subscribe for more tips like this!",
            "Click to find out how!",
            "Watch the full video for all the details.",
            "Like & subscribe for weekly updates!",
            "Start your journey today!",
        ]

        body_options = [
            (
                f"Discover everything about {keyword} in this comprehensive guide. "
                f"We cover tips, tricks, and strategies that actually work."
            ),
            (
                f"Looking for the best {keyword} advice? "
                f"This video breaks down the top methods step by step."
            ),
            (
                f"Learn how to master {keyword} with our proven approach. "
                f"Perfect for beginners and experienced creators alike."
            ),
            (
                f"In this video we dive deep into {keyword}. "
                f"You'll learn actionable tips you can apply immediately."
            ),
            (
                f"Struggling with {keyword}? We've got you covered. "
                f"Follow these simple steps and see real results fast."
            ),
            (
                f"The ultimate {keyword} tutorial for {datetime.now().year if True else 2026}. "
                f"Packed with practical advice and real-world examples."
            ),
        ]

        from datetime import datetime
        results: List[str] = []
        used_indices: set = set()

        for i, body in enumerate(body_options):
            if len(results) >= count:
                break
            desc = body
            if include_cta:
                desc = f"{desc} {random.choice(ctas)}"
            # Truncate to max_length at word boundary
            if len(desc) > max_length:
                desc = desc[: max_length - 3].rsplit(" ", 1)[0] + "..."
            results.append(desc)

        return results[:count]

    # ── hashtag / tag generation ─────────────────────────────────────────

    def generate_hashtags(
        self,
        keyword: str,
        platforms: Optional[List[Platform]] = None,
        count_per_platform: int = 10,
    ) -> Dict[str, List[str]]:
        """
        Generate platform-specific hashtags and tags.

        Args:
            keyword: The core topic keyword.
            platforms: List of Platform enums (defaults to all).
            count_per_platform: Max tags per platform.

        Returns:
            Dict mapping platform name -> list of hashtag strings.
        """
        if platforms is None:
            platforms = list(Platform)

        results: Dict[str, List[str]] = {}

        for platform in platforms:
            pool = list(self._PLATFORM_TAG_POOLS.get(platform.value, []))
            # Build keyword-derived tags
            kw_clean = re.sub(r"[^a-zA-Z\u4e00-\u9fff]", "", keyword)
            derived: List[str] = []

            if platform in (Platform.DOUYIN, Platform.XIAOHONGSHU):
                derived = [
                    f"#{kw_clean}",
                    f"#{kw_clean}教程",
                    f"#{kw_clean}分享",
                    f"#{kw_clean}日常",
                    f"#{kw_clean}攻略",
                    f"#{kw_clean}推荐",
                ]
            elif platform == Platform.BILIBILI:
                derived = [
                    f"#{kw_clean}",
                    f"#{kw_clean}教程",
                    f"#{kw_clean}分享",
                    f"#{kw_clean}入门",
                    f"#{kw_clean}技巧",
                    f"#{kw_clean}干货",
                ]
            elif platform == Platform.YOUTUBE:
                kw_lower = kw_clean.lower()
                derived = [
                    f"#{kw_lower}",
                    f"#{kw_lower}tips",
                    f"#{kw_lower}tutorial",
                    f"#{kw_lower}guide",
                    f"#{kw_lower}howto",
                    f"#{kw_lower}shorts",
                ]

            # Combine, deduplicate preserving order
            combined: List[str] = []
            seen: set = set()
            for tag in derived + pool:
                norm = tag.lower().lstrip("#")
                if norm not in seen:
                    seen.add(norm)
                    combined.append(tag if tag.startswith("#") else f"#{tag}")
                if len(combined) >= count_per_platform:
                    break

            results[platform.value] = combined

        return results

    def generate_tags_for_platform(
        self,
        keyword: str,
        platform: Platform,
        count: int = 15,
    ) -> List[str]:
        """Convenience wrapper: get tags for a single platform."""
        return self.generate_hashtags(keyword, [platform], count).get(
            platform.value, []
        )

    # ── keyword density ──────────────────────────────────────────────────

    def check_keyword_density(
        self,
        text: str,
        keywords: Optional[List[str]] = None,
        top_n: int = 15,
    ) -> Dict[str, float]:
        """
        Calculate keyword density for given or auto-detected keywords.

        Args:
            text: The full body text to analyze.
            keywords: Specific keywords to check. If None, top keywords
                      are auto-detected.
            top_n: Number of top keywords to return (auto-detect mode).

        Returns:
            Dict mapping keyword -> density percentage (0-100).
        """
        all_tokens = self._count_words(text)
        total = len(all_tokens)
        if total == 0:
            return {}

        freq: Dict[str, int] = {}
        for tok in all_tokens:
            freq[tok] = freq.get(tok, 0) + 1

        if keywords is not None:
            targets = [k.lower() for k in keywords]
            return {
                k: round((freq.get(k.lower(), 0) / total) * 100, 2)
                for k in keywords
            }

        # Auto-detect: sort by frequency, skip very short tokens
        sorted_kw = sorted(
            ((k, v) for k, v in freq.items() if len(k) > 2),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return {
            k: round((v / total) * 100, 2) for k, v in sorted_kw[:top_n]
        }

    def density_recommendations(
        self,
        density_map: Dict[str, float],
        primary_keyword: Optional[str] = None,
    ) -> List[str]:
        """
        Generate actionable recommendations based on keyword density.

        Ideal primary keyword density: 1-3%.
        Ideal secondary keywords: 0.5-1.5%.
        """
        recs: List[str] = []

        if primary_keyword:
            pk_lower = primary_keyword.lower()
            density = density_map.get(pk_lower, density_map.get(primary_keyword, 0))
            if density == 0:
                recs.append(
                    f"Primary keyword '{primary_keyword}' not found in text. "
                    f"Consider adding it 2-4 times naturally."
                )
            elif density < 1.0:
                recs.append(
                    f"Primary keyword '{primary_keyword}' density is {density}% "
                    f"(low). Aim for 1-3% for optimal SEO."
                )
            elif density > 3.0:
                recs.append(
                    f"Primary keyword '{primary_keyword}' density is {density}% "
                    f"(high / keyword-stuffing risk). Reduce to 1-3%."
                )
            else:
                recs.append(
                    f"Primary keyword '{primary_keyword}' density is {density}% — "
                    f"within the ideal 1-3% range."
                )

        # Check secondary keywords
        for kw, dens in density_map.items():
            if primary_keyword and kw.lower() == primary_keyword.lower():
                continue
            if dens > 3.5:
                recs.append(
                    f"Keyword '{kw}' has high density ({dens}%). "
                    f"Consider reducing to avoid over-optimization."
                )

        return recs

    # ── full analysis pipeline ───────────────────────────────────────────

    def analyze(
        self,
        keyword: str,
        body_text: str = "",
        *,
        title_count: int = 10,
        description_count: int = 3,
        platforms: Optional[List[Platform]] = None,
        tags_per_platform: int = 10,
        check_keywords: Optional[List[str]] = None,
    ) -> SEOAnalysis:
        """
        Run a full SEO analysis and return an SEOAnalysis bundle.

        Args:
            keyword: Primary keyword / topic.
            body_text: Video description or script body for density check.
            title_count: Number of titles to generate.
            description_count: Number of descriptions.
            platforms: Platforms for hashtag generation.
            tags_per_platform: Hashtags per platform.
            check_keywords: Specific keywords to check density for.

        Returns:
            SEOAnalysis with all results.
        """
        analysis = SEOAnalysis()

        # Titles
        analysis.titles = self.generate_titles(keyword, count=title_count)

        # Descriptions
        analysis.descriptions = self.generate_descriptions(
            keyword, count=description_count
        )

        # Hashtags
        analysis.hashtags = self.generate_hashtags(
            keyword, platforms=platforms, count_per_platform=tags_per_platform
        )

        # Keyword density (if body text provided)
        if body_text.strip():
            analysis.keyword_density = self.check_keyword_density(
                body_text, keywords=check_keywords
            )
            analysis.recommendations = self.density_recommendations(
                analysis.keyword_density, primary_keyword=keyword
            )

        return analysis

    def analyze_and_print(
        self,
        keyword: str,
        body_text: str = "",
        **kwargs,
    ) -> SEOAnalysis:
        """Run analysis and pretty-print results to stdout."""
        result = self.analyze(keyword, body_text, **kwargs)

        print("=" * 60)
        print(f"  SEO ANALYSIS: {keyword}")
        print("=" * 60)

        print("\n📌 VIRAL TITLE IDEAS:")
        for i, title in enumerate(result.titles, 1):
            print(f"  {i}. {title}")

        print("\n📝 META DESCRIPTIONS:")
        for i, desc in enumerate(result.descriptions, 1):
            print(f"  {i}. {desc}")

        print("\n#️⃣ HASHTAGS BY PLATFORM:")
        for platform, tags in result.hashtags.items():
            print(f"  [{platform.upper()}]")
            print(f"    {' | '.join(tags)}")

        if result.keyword_density:
            print("\n📊 KEYWORD DENSITY:")
            for kw, dens in result.keyword_density.items():
                bar = "█" * int(dens * 5) + "░" * (25 - int(dens * 5))
                print(f"  {kw:<20} {dens:>5.2f}%  {bar}")

        if result.recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for rec in result.recommendations:
                print(f"  • {rec}")

        print()
        return result


# ── module-level convenience ─────────────────────────────────────────────

_default_optimizer = SEOOptimizer()


def generate_viral_titles(keyword: str, **kwargs) -> List[str]:
    """Convenience function: generate viral titles."""
    return _default_optimizer.generate_titles(keyword, **kwargs)


def generate_meta_descriptions(keyword: str, **kwargs) -> List[str]:
    """Convenience function: generate meta descriptions."""
    return _default_optimizer.generate_descriptions(keyword, **kwargs)


def generate_platform_hashtags(
    keyword: str, platforms: Optional[List[Platform]] = None, **kwargs
) -> Dict[str, List[str]]:
    """Convenience function: generate hashtags for platforms."""
    return _default_optimizer.generate_hashtags(keyword, platforms, **kwargs)


def check_density(
    text: str, keywords: Optional[List[str]] = None, **kwargs
) -> Dict[str, float]:
    """Convenience function: check keyword density."""
    return _default_optimizer.check_keyword_density(text, keywords, **kwargs)


def full_seo_analysis(keyword: str, body_text: str = "", **kwargs) -> SEOAnalysis:
    """Convenience function: run full SEO analysis."""
    return _default_optimizer.analyze(keyword, body_text, **kwargs)

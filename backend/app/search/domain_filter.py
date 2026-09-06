"""
Domain filter, safety validator, and social platform priority scoring for TRACE.
Filters out spam/NSFW scraper domains, adult subreddits, and elevates authentic platforms.
"""

import re
from urllib.parse import urlparse

# Authentic social & media platforms given priority ranking
SOCIAL_DOMAINS = {
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "reddit.com",
    "pinterest.com",
    "linkedin.com",
    "tiktok.com",
    "youtube.com",
    "threads.net",
    "github.com",
    "wikipedia.org",
    "medium.com",
    "flickr.com",
    "tumblr.com",
    "quora.com",
    "news.ycombinator.com",
    "wired.com",
    "bbc.com",
    "nytimes.com",
    "reuters.com",
    "theguardian.com",
    "forbes.com",
    "techcrunch.com",
    "bloomberg.com",
    "ndtv.com",
    "thehindu.com",
    "indianexpress.com",
}

# Strict NSFW / Adult / Spam keywords checked in URL, title, and snippet
BLOCKED_KEYWORDS = [
    "porn",
    "xxx",
    "nude",
    "nudity",
    "nsfw",
    "adult",
    "sex",
    "sexy",
    "erotic",
    "hentai",
    "camgirl",
    "escort",
    "onlyfans",
    "fansly",
    "coomer",
    "gooner",
    "gonewild",
    "fap",
    "slut",
    "tits",
    "boobs",
    "ass",
    "pussy",
    "milf",
    "bdsm",
    "fetish",
    "bikini",
    "lingerie",
    "stripper",
    "underwear",
    "playboy",
    "centerfold",
    "bunkr",
    "thothub",
    "simpcity",
    "anonfiles",
    "cyberdrop",
    "xvideos",
    "pornhub",
    "redtube",
    "spankbang",
    "leaked",
    "leaks",
    "celeb-nudes",
    "candies",
    "rule34",
]


def extract_root_domain(url: str) -> str:
    """Extract root domain (e.g. reddit.com from www.reddit.com)."""
    try:
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""


def is_safe_content(url: str, title: str = "", snippet: str = "") -> bool:
    """
    Comprehensive SafeSearch check across URL path, domain, title, and snippet.
    Returns False if any NSFW, adult subreddit, or explicit token is present.
    """
    combined_text = f"{url.lower()} {title.lower()} {snippet.lower()}"

    # Check for blocked keywords
    for kw in BLOCKED_KEYWORDS:
        # Match whole words or standard URL path slugs
        pattern = r"(?:^|[/_.\-\s?=&])" + re.escape(kw) + r"(?:[/_.\-\s?=&]|$)"
        if re.search(pattern, combined_text) or kw in url.lower():
            return False

    return True


def is_safe_domain(url: str) -> bool:
    """Convenience alias for URL safety checking."""
    return is_safe_content(url)


def is_social_platform(url: str) -> bool:
    """Check if URL belongs to a recognized social network or major media publication."""
    domain = extract_root_domain(url)
    for social in SOCIAL_DOMAINS:
        if domain == social or domain.endswith("." + social):
            return True
    return False


def get_domain_priority_boost(url: str) -> float:
    """Return priority score boost for social networks and trusted sources."""
    if is_social_platform(url):
        return 0.08  # Boost to prioritize social networks over obscure blogs
    return 0.0

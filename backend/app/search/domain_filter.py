"""
Domain filter, safety validator, and social platform priority scoring for TRACE.
Filters out spam/NSFW scraper domains and elevates authentic social & media platforms.
"""

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
}

# Suspicious / NSFW / spam keywords in domain or URL
BLOCKED_KEYWORDS = [
    "porn",
    "xxx",
    "nude",
    "nsfw",
    "adult",
    "sex",
    "erotic",
    "hentai",
    "camgirl",
    "escort",
    "onlyfans-leak",
    "coomer",
    "gooner",
    "anonfiles",
    "bunkr",
    "thothub",
    "fap",
    "xvideos",
    "pornhub",
    "redtube",
    "spankbang",
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


def is_safe_domain(url: str) -> bool:
    """Check if URL domain is safe (filters out NSFW, scam, and adult scrapers)."""
    url_lower = url.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in url_lower:
            return False
    return True


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
        return 0.05  # Slight boost to elevate social platforms when similarity is tied
    return 0.0

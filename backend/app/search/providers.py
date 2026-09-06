"""
Search provider abstraction for reverse image search.
Supports SerpAPI (Google Lens), Bing Visual Search, and a test-only mock.
"""

import base64
import hashlib
import json
import logging
import os
import re
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

# Load .env at module import
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv()

logger = logging.getLogger("trace.search.providers")


@dataclass
class SearchResult:
    """A candidate result from reverse image search."""

    source_url: str
    page_title: str = ""
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    domain: str = ""
    snippet: str = ""
    published_date: Optional[str] = None

    def __post_init__(self):
        if not self.domain and self.source_url:
            try:
                self.domain = urlparse(self.source_url).netloc
            except Exception:
                pass


class SearchProvider(ABC):
    """Abstract base class for reverse image search providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display and logging."""
        ...

    @abstractmethod
    async def search(
        self, image_bytes: bytes, max_results: int = 10
    ) -> List[SearchResult]:
        """Execute reverse image search and return candidate results."""
        ...


async def upload_temp_image(image_bytes: bytes) -> Optional[str]:
    """Upload image bytes to an ephemeral public host for SerpAPI visual search."""
    # Try catbox.moe first (direct raw image serving, Google-accessible)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            files = {"fileToUpload": ("trace_query.jpg", image_bytes, "image/jpeg")}
            data = {"reqtype": "fileupload"}
            response = await client.post("https://catbox.moe/user/api.php", data=data, files=files)
            if response.status_code == 200 and response.text.startswith("http"):
                url = response.text.strip()
                logger.info("Uploaded query image to Catbox: %s", url)
                return url
    except Exception as e:
        logger.warning("catbox.moe upload failed: %s", e)

    # Fallback to tmpfiles.org
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            files = {"file": ("trace_query.jpg", image_bytes, "image/jpeg")}
            response = await client.post("https://tmpfiles.org/api/v1/upload", files=files)
            if response.status_code == 200:
                data = response.json()
                raw_url = data.get("data", {}).get("url", "")
                if raw_url:
                    direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                    logger.info("Uploaded query image to tmpfiles: %s", direct_url)
                    return direct_url
    except Exception as e:
        logger.warning("tmpfiles.org upload failed: %s", e)

    return None


class SerpAPIProvider(SearchProvider):
    """
    Reverse image search via SerpAPI Google Lens endpoint.
    Requires SERPAPI_API_KEY environment variable or constructor argument.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "SERPAPI_API_KEY is required for SerpAPIProvider. "
                "Set it in .env or as an environment variable."
            )
        self.base_url = "https://serpapi.com/search.json"

    @property
    def name(self) -> str:
        return "SerpAPI Google Lens"

    async def search(
        self, image_bytes: bytes, max_results: int = 10
    ) -> List[SearchResult]:
        """Search using SerpAPI Google Lens."""
        results: List[SearchResult] = []

        # 1. Upload image to ephemeral host so Google Lens can process it
        image_public_url = await upload_temp_image(image_bytes)
        if not image_public_url:
            logger.error("Could not obtain public URL for image query")
            return results

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                params = {
                    "engine": "google_lens",
                    "url": image_public_url,
                    "api_key": self.api_key,
                    "hl": "en",
                    "safe": "active",
                }
                response = await client.get(self.base_url, params=params)

                if response.status_code != 200:
                    logger.error(
                        "SerpAPI returned status %d: %s",
                        response.status_code,
                        response.text[:500],
                    )
                    return results

                data = response.json()

                # Parse visual matches
                visual_matches = data.get("visual_matches", [])
                for match in visual_matches[:max_results]:
                    results.append(
                        SearchResult(
                            source_url=match.get("link", ""),
                            page_title=match.get("title", ""),
                            image_url=match.get("image", match.get("original", match.get("thumbnail", ""))),
                            thumbnail_url=match.get("thumbnail", ""),
                            domain=match.get("source", ""),
                            snippet=match.get("snippet", ""),
                        )
                    )

                # Parse knowledge graph & image results if visual matches empty
                if not results:
                    for key in ["knowledge_graph", "organic_results", "images_results", "reverse_image_search"]:
                        items = data.get(key, [])
                        if isinstance(items, dict):
                            items = [items]
                        for item in items[:max_results]:
                            results.append(
                                SearchResult(
                                    source_url=item.get("link", item.get("source_url", "")),
                                    page_title=item.get("title", item.get("name", "")),
                                    image_url=item.get("original", item.get("image", item.get("thumbnail", ""))),
                                    thumbnail_url=item.get("thumbnail", ""),
                                    domain=item.get("source", ""),
                                    snippet=item.get("snippet", ""),
                                )
                            )

        except Exception as e:
            logger.error("SerpAPI request failed: %s", e)

        # Filter empty source URLs
        valid_results = [r for r in results if r.source_url]
        logger.info("SerpAPI returned %d candidate results", len(valid_results))
        return valid_results[:max_results]


class BingVisualSearchProvider(SearchProvider):
    """
    Reverse image search via Bing Visual Search API v7.
    Requires BING_SEARCH_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BING_SEARCH_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "BING_SEARCH_API_KEY is required for BingVisualSearchProvider. "
                "Set it in .env or as an environment variable."
            )
        self.endpoint = "https://api.bing.microsoft.com/v7.0/images/visualsearch"

    @property
    def name(self) -> str:
        return "Bing Visual Search"

    async def search(
        self, image_bytes: bytes, max_results: int = 10
    ) -> List[SearchResult]:
        """Search using Bing Visual Search API with direct image upload."""
        results: List[SearchResult] = []
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    files={"image": ("image.jpg", image_bytes, "image/jpeg")},
                )

                if response.status_code != 200:
                    logger.error(
                        "Bing Visual Search returned status %d: %s",
                        response.status_code,
                        response.text[:500],
                    )
                    return results

                data = response.json()

                for tag in data.get("tags", []):
                    for action in tag.get("actions", []):
                        action_type = action.get("actionType", "")
                        if action_type == "PagesIncluding":
                            for item in action.get("data", {}).get("value", [])[:max_results]:
                                results.append(
                                    SearchResult(
                                        source_url=item.get("hostPageUrl", ""),
                                        page_title=item.get("name", ""),
                                        image_url=item.get("contentUrl", ""),
                                        thumbnail_url=item.get("thumbnailUrl", ""),
                                        domain=item.get("hostPageDisplayUrl", ""),
                                        snippet=item.get("snippet", ""),
                                        published_date=item.get("datePublished"),
                                    )
                                )
                        elif action_type == "VisualSearch":
                            for item in action.get("data", {}).get("value", [])[:max_results]:
                                results.append(
                                    SearchResult(
                                        source_url=item.get("hostPageUrl", ""),
                                        page_title=item.get("name", ""),
                                        image_url=item.get("contentUrl", ""),
                                        thumbnail_url=item.get("thumbnailUrl", ""),
                                    )
                                )

        except httpx.HTTPError as e:
            logger.error("Bing Visual Search request failed: %s", e)

        seen_urls = set()
        unique_results = []
        for r in results:
            if r.source_url and r.source_url not in seen_urls:
                seen_urls.add(r.source_url)
                unique_results.append(r)

        return unique_results[:max_results]


class MockSearchProvider(SearchProvider):
    """Mock search provider for unit testing ONLY."""

    @property
    def name(self) -> str:
        return "Mock (TEST ONLY)"

    async def search(
        self, image_bytes: bytes, max_results: int = 10
    ) -> List[SearchResult]:
        logger.warning("MockSearchProvider is active — results are NOT from real search")
        img_hash = hashlib.sha256(image_bytes).hexdigest()[:12]
        return [
            SearchResult(
                source_url=f"https://example.com/mock-result/{img_hash}",
                page_title=f"[MOCK] Test Result for {img_hash}",
                image_url=f"https://example.com/mock-image/{img_hash}.jpg",
                thumbnail_url="",
                domain="example.com",
                snippet="This is a MOCK search result for testing only.",
            )
        ]


def get_search_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> SearchProvider:
    """Factory function to create configured SearchProvider."""
    name = (provider_name or os.getenv("SEARCH_PROVIDER", "serpapi")).lower().strip()

    if name == "serpapi":
        return SerpAPIProvider(api_key=api_key)
    elif name == "bing":
        return BingVisualSearchProvider(api_key=api_key)
    elif name == "mock":
        return MockSearchProvider()
    else:
        raise ValueError(
            f"Unknown search provider '{name}'. Supported: serpapi, bing, mock"
        )

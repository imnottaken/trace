"""
Candidate matcher: downloads candidate images, runs face detection,
computes cosine similarity against input embedding, filters NSFW/spam, and ranks matches.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import List, Optional

import httpx
import numpy as np
from backend.app.ml.face_engine import FaceEngine, get_face_engine
from backend.app.search.domain_filter import (
    extract_root_domain,
    get_domain_priority_boost,
    is_safe_content,
    is_safe_domain,
    is_social_platform,
)
from backend.app.search.providers import SearchResult

logger = logging.getLogger("trace.search.candidate_matcher")


@dataclass
class MatchedCandidate:
    """A search result that has been face-verified with similarity scoring."""

    search_result: SearchResult
    similarity_score: float  # 0.0 - 1.0 cosine similarity
    calibrated_score: float  # 0.0 - 100.0 calibrated percentage
    face_detected: bool
    is_social: bool = False
    image_bytes: Optional[bytes] = None
    image_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "source_url": self.search_result.source_url,
            "page_title": self.search_result.page_title,
            "image_url": self.search_result.image_url,
            "thumbnail_url": self.search_result.thumbnail_url,
            "domain": self.search_result.domain,
            "snippet": self.search_result.snippet,
            "similarity_score": round(self.similarity_score, 4),
            "calibrated_score": round(self.calibrated_score, 2),
            "face_detected": self.face_detected,
            "is_social": self.is_social,
            "image_hash": self.image_hash,
        }


async def download_image(url: str, timeout: float = 15.0) -> Optional[bytes]:
    """Download an image from a URL, returning bytes or None on failure."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/*,*/*;q=0.8",
            },
        ) as client:
            response = await client.get(url)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "image" in content_type or len(response.content) > 1000:
                    return response.content
            return None
    except Exception as e:
        logger.debug("Failed to download image from %s: %s", url, e)
        return None


async def match_candidates(
    input_embedding: np.ndarray,
    candidates: List[SearchResult],
    face_engine: Optional[FaceEngine] = None,
    similarity_threshold: float = 0.3,
    max_candidates: int = 15,
) -> List[MatchedCandidate]:
    """
    Download candidate images, detect faces, compute similarity, and rank with safety guards.
    """
    if face_engine is None:
        face_engine = get_face_engine()

    matched: List[MatchedCandidate] = []

    # 1. Filter out unsafe / spam / adult scraper domains and NSFW subreddits/titles
    safe_candidates = [
        c for c in candidates
        if is_safe_content(c.source_url, c.page_title, c.snippet)
    ]

    for i, candidate in enumerate(safe_candidates[:max_candidates]):
        image_url = candidate.image_url or candidate.thumbnail_url
        if not image_url:
            continue

        domain_label = candidate.domain or extract_root_domain(candidate.source_url)
        is_social = is_social_platform(candidate.source_url)

        logger.info(
            "Evaluating candidate %d/%d: %s (social=%s)",
            i + 1,
            min(len(safe_candidates), max_candidates),
            domain_label,
            is_social,
        )

        image_bytes = await download_image(image_url)
        if image_bytes is None and candidate.thumbnail_url and candidate.thumbnail_url != image_url:
            image_bytes = await download_image(candidate.thumbnail_url)

        if image_bytes is None:
            continue

        try:
            detections = face_engine.detect_faces(image_bytes)
            if not detections:
                matched.append(
                    MatchedCandidate(
                        search_result=candidate,
                        similarity_score=0.0,
                        calibrated_score=0.0,
                        face_detected=False,
                        is_social=is_social,
                        image_bytes=image_bytes,
                    )
                )
                continue

            primary = detections[0]
            if primary.embedding is None:
                continue

            sim_result = FaceEngine.compute_similarity(
                input_embedding, primary.embedding
            )

            img_hash = hashlib.sha256(image_bytes).hexdigest()

            matched.append(
                MatchedCandidate(
                    search_result=candidate,
                    similarity_score=sim_result["cosine_similarity"],
                    calibrated_score=sim_result["calibrated_score"],
                    face_detected=True,
                    is_social=is_social,
                    image_bytes=image_bytes,
                    image_hash=img_hash,
                )
            )

        except Exception as e:
            logger.warning("Error processing candidate %d: %s", i, e)
            continue

    # 2. Ranking algorithm: sort by cosine similarity + social platform priority boost
    def candidate_rank_score(m: MatchedCandidate) -> float:
        boost = get_domain_priority_boost(m.search_result.source_url)
        return m.similarity_score + boost

    matched.sort(key=candidate_rank_score, reverse=True)

    # 3. Filter by threshold
    filtered = [m for m in matched if m.similarity_score >= similarity_threshold]

    logger.info(
        "Matched %d safe candidates (%d above threshold %.2f)",
        len(matched),
        len(filtered),
        similarity_threshold,
    )

    return filtered

"""
Candidate matcher: downloads candidate images, runs face detection,
computes cosine similarity against input embedding, and ranks matches.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

import httpx
import numpy as np

from backend.app.ml.face_engine import FaceEngine, get_face_engine
from backend.app.search.providers import SearchResult

logger = logging.getLogger("trace.search.candidate_matcher")


@dataclass
class MatchedCandidate:
    """A search result that has been face-verified with similarity scoring."""

    search_result: SearchResult
    similarity_score: float  # 0.0 - 1.0 cosine similarity
    calibrated_score: float  # 0.0 - 100.0 calibrated percentage
    face_detected: bool
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
                "User-Agent": "Mozilla/5.0 (compatible; TRACE-Bot/1.0)",
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
    max_candidates: int = 10,
) -> List[MatchedCandidate]:
    """
    Download candidate images, detect faces, compute similarity, and rank.

    Args:
        input_embedding: 512-d unit-normalized embedding of input face.
        candidates: Search results to evaluate.
        face_engine: FaceEngine instance (uses singleton if None).
        similarity_threshold: Minimum cosine similarity to include.
        max_candidates: Maximum candidates to evaluate.

    Returns:
        List of MatchedCandidate sorted by similarity (descending).
    """
    if face_engine is None:
        face_engine = get_face_engine()

    matched: List[MatchedCandidate] = []

    for i, candidate in enumerate(candidates[:max_candidates]):
        # Try image_url first, then thumbnail
        image_url = candidate.image_url or candidate.thumbnail_url
        if not image_url:
            logger.debug("Candidate %d has no image URL, skipping", i)
            continue

        logger.info(
            "Evaluating candidate %d/%d: %s",
            i + 1,
            min(len(candidates), max_candidates),
            candidate.domain or candidate.source_url[:60],
        )

        image_bytes = await download_image(image_url)
        if image_bytes is None:
            # Try thumbnail as fallback
            if candidate.thumbnail_url and candidate.thumbnail_url != image_url:
                image_bytes = await download_image(candidate.thumbnail_url)
            if image_bytes is None:
                logger.debug("Could not download image for candidate %d", i)
                continue

        try:
            # Detect face in candidate image
            detections = face_engine.detect_faces(image_bytes)
            if not detections:
                matched.append(
                    MatchedCandidate(
                        search_result=candidate,
                        similarity_score=0.0,
                        calibrated_score=0.0,
                        face_detected=False,
                        image_bytes=image_bytes,
                    )
                )
                continue

            # Get primary face embedding
            primary = detections[0]
            if primary.embedding is None:
                continue

            # Compute similarity
            sim_result = FaceEngine.compute_similarity(
                input_embedding, primary.embedding
            )

            import hashlib

            img_hash = hashlib.sha256(image_bytes).hexdigest()

            matched.append(
                MatchedCandidate(
                    search_result=candidate,
                    similarity_score=sim_result["cosine_similarity"],
                    calibrated_score=sim_result["calibrated_score"],
                    face_detected=True,
                    image_bytes=image_bytes,
                    image_hash=img_hash,
                )
            )

        except Exception as e:
            logger.warning("Error processing candidate %d: %s", i, e)
            continue

    # Sort by similarity descending
    matched.sort(key=lambda m: m.similarity_score, reverse=True)

    # Filter by threshold
    filtered = [m for m in matched if m.similarity_score >= similarity_threshold]

    logger.info(
        "Matched %d candidates (%d above threshold %.2f)",
        len(matched),
        len(filtered),
        similarity_threshold,
    )

    return filtered

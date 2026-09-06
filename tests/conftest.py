"""
Pytest configuration and opaque-box test oracles for Project TRACE E2E Test Suite.
Provides deterministic cryptographic reference models, schema validators,
fixture paths, and synthetic test helpers.
"""

import os
import json
import hashlib
import re
import pytest
from typing import Dict, Any, Tuple, Optional

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TESTS_DIR, "fixtures")
ROOT_DIR = os.path.dirname(TESTS_DIR)

# --- 1. Fixture File Paths ---

@pytest.fixture
def fixtures_dir() -> str:
    return FIXTURES_DIR

@pytest.fixture
def clean_portrait_path() -> str:
    return os.path.join(FIXTURES_DIR, "clean_portrait.png")

@pytest.fixture
def clean_portrait_bytes(clean_portrait_path) -> bytes:
    with open(clean_portrait_path, "rb") as f:
        return f.read()

@pytest.fixture
def multi_face_portrait_path() -> str:
    return os.path.join(FIXTURES_DIR, "multi_face_portrait.png")

@pytest.fixture
def multi_face_portrait_bytes(multi_face_portrait_path) -> bytes:
    with open(multi_face_portrait_path, "rb") as f:
        return f.read()

@pytest.fixture
def non_face_pattern_path() -> str:
    return os.path.join(FIXTURES_DIR, "non_face_pattern.png")

@pytest.fixture
def non_face_pattern_bytes(non_face_pattern_path) -> bytes:
    with open(non_face_pattern_path, "rb") as f:
        return f.read()

@pytest.fixture
def tampered_clone_path() -> str:
    return os.path.join(FIXTURES_DIR, "tampered_clone.png")

@pytest.fixture
def tampered_clone_bytes(tampered_clone_path) -> bytes:
    with open(tampered_clone_path, "rb") as f:
        return f.read()

@pytest.fixture
def corrupted_image_path() -> str:
    return os.path.join(FIXTURES_DIR, "corrupted_image.bin")

@pytest.fixture
def corrupted_image_bytes(corrupted_image_path) -> bytes:
    with open(corrupted_image_path, "rb") as f:
        return f.read()

@pytest.fixture
def sample_metadata_path() -> str:
    return os.path.join(FIXTURES_DIR, "metadata_sample.json")


# --- 2. Deterministic Cryptographic Oracle ---

class CryptographicOracle:
    """Authoritative reference implementation of RFC 8785 Canonical Serialization
    and Two-Tier SHA-256 Content Fingerprinting."""

    @staticmethod
    def compute_raw_sha256(data: bytes) -> str:
        """Compute lower-case hex SHA-256 digest of raw binary data."""
        return hashlib.sha256(data).hexdigest().lower()

    @staticmethod
    def normalize_url(raw_url: str) -> str:
        """Normalize URL: strip tracking parameters, lowercase scheme & host, strip trailing slash."""
        raw_url = raw_url.strip()
        if not raw_url:
            return ""
        from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
        try:
            parsed = urlparse(raw_url)
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path
            if len(path) > 1 and path.endswith("/"):
                path = path[:-1]
            # Strip tracking query params
            filtered_query = []
            for k, v in parse_qsl(parsed.query, keep_blank_values=True):
                k_lower = k.lower()
                if (k_lower.startswith("utm_") or 
                    k_lower in ("fbclid", "gclid", "ref", "source")):
                    continue
                filtered_query.append((k, v))
            filtered_query.sort(key=lambda x: x[0])
            query_str = urlencode(filtered_query)
            return urlunparse((scheme, netloc, path, parsed.params, query_str, parsed.fragment))
        except Exception:
            return raw_url.strip().lower()

    @staticmethod
    def normalize_title(title: str) -> str:
        """Collapse whitespace and trim title text."""
        return " ".join(title.strip().split())

    @classmethod
    def build_canonical_metadata(
        cls,
        image_sha256: str,
        source_url: str,
        title: str,
        timestamp: int
    ) -> str:
        """Deterministic RFC 8785 canonical JSON string with lexicographical key ordering
        and no token whitespace."""
        payload = {
            "image_sha256": image_sha256.lower().replace("0x", ""),
            "source_url": cls.normalize_url(source_url),
            "timestamp": int(timestamp),
            "title": cls.normalize_title(title),
        }
        # Strictly sort keys lexicographically, zero whitespace separators
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def generate_composite_fingerprint(
        cls,
        image_bytes: bytes,
        source_url: str,
        title: str,
        timestamp: int
    ) -> Dict[str, Any]:
        """Compute composite EVM bytes32 hash from raw image bytes and provenance metadata."""
        image_sha256 = cls.compute_raw_sha256(image_bytes)
        canonical_json = cls.build_canonical_metadata(image_sha256, source_url, title, timestamp)
        composite_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest().lower()
        bytes32_hex = f"0x{composite_hash}"
        return {
            "image_sha256": image_sha256,
            "canonical_json": canonical_json,
            "bytes32_hex": bytes32_hex,
            "raw_digest": composite_hash,
        }

    @staticmethod
    def find_byte_divergence(bytes_a: bytes, bytes_b: bytes) -> Tuple[bool, int]:
        """Return (is_identical, first_divergence_byte_offset)."""
        if bytes_a == bytes_b:
            return True, -1
        min_len = min(len(bytes_a), len(bytes_b))
        for i in range(min_len):
            if bytes_a[i] != bytes_b[i]:
                return False, i
        return False, min_len


@pytest.fixture
def crypto_oracle() -> CryptographicOracle:
    return CryptographicOracle()


# --- 3. TraceProof Smart Contract Oracle ---

class TraceProofContractOracle:
    """Authoritative EVM state model mirroring TraceProof.sol invariants."""

    def __init__(self):
        self.evidence_store: Dict[str, Dict[str, Any]] = {}
        self.evidence_hashes = []
        self.current_block = 42100000
        self.current_timestamp = 1725562800

    def is_valid_bytes32(self, h: str) -> bool:
        if not isinstance(h, str):
            return False
        if not h.startswith("0x"):
            return False
        hex_part = h[2:]
        if len(hex_part) != 64:
            return False
        if not re.fullmatch(r"[0-9a-fA-F]{64}", hex_part):
            return False
        if hex_part == "0" * 64:
            return False  # bytes32(0) is rejected by contract
        return True

    def record_evidence(self, content_hash: str, source_reference: str, sender: str = "0x9965507D1a55bcC2695C58ba16FB37d819B0A4df") -> Dict[str, Any]:
        h_norm = content_hash.lower()
        if not self.is_valid_bytes32(h_norm):
            raise ValueError("InvalidContentHash")
        if not source_reference or len(source_reference.strip()) == 0:
            raise ValueError("EmptySourceReference")
        if h_norm in self.evidence_store:
            raise ValueError(f"EvidenceAlreadyExists({h_norm})")

        self.current_block += 1
        self.current_timestamp += 2
        record = {
            "content_hash": h_norm,
            "source_reference": source_reference,
            "timestamp": self.current_timestamp,
            "block_number": self.current_block,
            "recorded_by": sender,
            "exists": True,
        }
        self.evidence_store[h_norm] = record
        self.evidence_hashes.append(h_norm)
        return record

    def get_evidence(self, content_hash: str) -> Dict[str, Any]:
        h_norm = content_hash.lower()
        if h_norm not in self.evidence_store:
            raise KeyError(f"EvidenceNotFound({h_norm})")
        return self.evidence_store[h_norm]

    def verify_evidence(self, content_hash: str) -> Tuple[bool, int]:
        h_norm = content_hash.lower()
        if h_norm in self.evidence_store:
            rec = self.evidence_store[h_norm]
            return True, rec["timestamp"]
        return False, 0


@pytest.fixture
def contract_oracle() -> TraceProofContractOracle:
    return TraceProofContractOracle()


# --- 4. Mathematical Cosine Similarity & Calibration Oracle ---

class SimilarityOracle:
    """Authoritative reference for 512-d ArcFace vector comparison and calibration."""

    @staticmethod
    def cosine_similarity(vec_a, vec_b) -> float:
        import numpy as np
        a = np.asarray(vec_a, dtype=np.float32)
        b = np.asarray(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        dot = np.dot(a, b)
        sim = float(dot / (norm_a * norm_b))
        return max(-1.0, min(1.0, sim))

    @classmethod
    def calibrated_score(cls, vec_a, vec_b) -> float:
        """Calibrate cosine similarity [-1, 1] to human-interpretable percentage [0, 100]."""
        cos_sim = cls.cosine_similarity(vec_a, vec_b)
        # Standard ArcFace calibrated mapping: 0.0 sim = 50%, 1.0 sim = 100%, -1.0 sim = 0%
        # Or threshold-aligned: cos >= 0.4 starts positive match range
        percentage = (cos_sim + 1.0) / 2.0 * 100.0
        return round(max(0.0, min(100.0, percentage)), 2)


@pytest.fixture
def sim_oracle() -> SimilarityOracle:
    return SimilarityOracle()


# --- 5. Design System Tokens & Brand Asset Verification ---

GOA_PALETTE = {
    "deep_green": "#006B3C",
    "ink_black_green": "#082F1C",
    "deep_goa_green": "#05472A",
    "sunflower_yellow": "#F7E000",
    "hot_pink": "#FF0A87",
    "cream": "#F5E7A1",
}

BRAND_DEVANAGARI = "चेहरा → सबूत"
BRAND_SUBTITLE = "DISCOVER · VERIFY · PROVE"

@pytest.fixture
def design_tokens() -> Dict[str, Any]:
    return {
        "palette": GOA_PALETTE,
        "devanagari": BRAND_DEVANAGARI,
        "subtitle": BRAND_SUBTITLE,
    }

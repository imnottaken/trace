"""Deterministic Two-Tier SHA-256 Content Fingerprinting for Project TRACE.

Implements RFC 8785 canonical metadata serialization + SHA-256 digest generation
guaranteeing 100% mathematical determinism and cross-language parity with TypeScript.
"""

import hashlib
import json
import re
import unicodedata
from typing import Any, Dict, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlparse

# WHATWG URL path characters that must remain unencoded
WHATWG_PATH_SAFE = "/:@!$&'()*+,;=-_.~%[]^|"


def normalize_url(raw_url: str) -> str:
    """Normalizes a source URL by lowercasing scheme and domain, converting IDN hostnames
    to Punycode, handling IPv6 brackets, standardizing paths with WHATWG percent-encoding,
    stripping tracking parameters, and deterministically sorting query parameters by (key, value)
    to match WHATWG URL standard and cryptographic canonicalization.
    """
    trimmed = unicodedata.normalize("NFC", raw_url).strip()
    if not trimmed:
        return ""

    try:
        parsed = urlparse(trimmed)
        scheme = parsed.scheme.lower() if parsed.scheme else "https"
        hostname = parsed.hostname.lower() if parsed.hostname else ""

        if not hostname:
            return trimmed.lower()

        # Convert Internationalized Domain Names (IDN) to Punycode A-labels
        try:
            hostname = hostname.encode("idna").decode("ascii")
        except Exception:
            pass

        # Handle port stripping and IPv6 bracket formatting
        port = parsed.port
        is_ipv6 = ":" in hostname and not hostname.startswith("[")
        formatted_host = f"[{hostname}]" if is_ipv6 else hostname

        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443) or port is None:
            netloc = formatted_host
        else:
            netloc = f"{formatted_host}:{port}"

        # Standardize path: preserve matrix params, default to "/" if empty, strip trailing slash if len > 1
        path = f"{parsed.path};{parsed.params}" if parsed.params else parsed.path
        if not path:
            path = "/"
        elif len(path) > 1 and path.endswith("/"):
            path = path[:-1]

        # Standardize WHATWG percent-encoding for non-ASCII path characters and spaces
        path = quote(path, safe=WHATWG_PATH_SAFE)

        # Strip tracking query params and sort remaining by (key, value)
        filtered_queries = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")
            and k.lower() not in {"fbclid", "gclid", "ref", "source"}
        ]
        filtered_queries.sort(key=lambda item: (item[0], item[1]))

        # Format query string to match WHATWG application/x-www-form-urlencoded
        query = urlencode(filtered_queries, safe="*").replace("~", "%7E")

        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        query_str = f"?{query}" if query else ""

        return f"{scheme}://{netloc}{path}{query_str}{fragment}"
    except Exception:
        return trimmed.lower()


def normalize_title(title: str) -> str:
    """Normalizes text by applying Unicode NFC normalization, collapsing whitespace,
    and trimming leading/trailing whitespace.
    """
    nfc_title = unicodedata.normalize("NFC", title)
    return re.sub(r"\s+", " ", nfc_title.strip())


def compute_raw_image_hash(image_bytes: bytes) -> str:
    """Computes SHA-256 hex digest of raw binary image data."""
    return hashlib.sha256(image_bytes).hexdigest().lower()


def build_canonical_metadata(
    image_sha256: str, source_url: str, title: str, timestamp: int
) -> str:
    """Produces deterministic RFC 8785 canonical JSON string.

    Lexicographical key sorting and zero whitespace between tokens.
    """
    clean_hash = image_sha256.lower()
    if clean_hash.startswith("0x"):
        clean_hash = clean_hash[2:]

    payload: Dict[str, Any] = {
        "image_sha256": clean_hash,
        "source_url": normalize_url(source_url),
        "timestamp": int(timestamp),
        "title": normalize_title(title),
    }

    # RFC 8785: sorted keys, no whitespace around separators
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def generate_composite_fingerprint(
    image_bytes: bytes, source_url: str, title: str, timestamp: int
) -> Tuple[str, str, str, bytes]:
    """Generates deterministic composite fingerprint for EVM notarization.

    Returns: (bytes32_hex, canonical_json_str, image_sha256, raw_bytes32)
    """
    image_sha256 = compute_raw_image_hash(image_bytes)
    canonical_json = build_canonical_metadata(image_sha256, source_url, title, timestamp)
    composite_digest = hashlib.sha256(canonical_json.encode("utf-8")).digest()
    bytes32_hex = "0x" + composite_digest.hex().lower()

    return bytes32_hex, canonical_json, image_sha256, composite_digest

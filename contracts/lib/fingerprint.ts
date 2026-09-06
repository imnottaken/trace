import * as crypto from "crypto";

/**
 * Normalizes a source URL by lowercasing scheme and domain, stripping tracking parameters,
 * and normalizing trailing slashes.
 */
export function normalizeUrl(rawUrl: string): string {
  const trimmed = rawUrl.normalize("NFC").trim();
  if (!trimmed) return "";

  try {
    const parsed = new URL(trimmed);
    parsed.protocol = parsed.protocol.toLowerCase();
    parsed.hostname = parsed.hostname.toLowerCase();

    // Strip common tracking and referrer query parameters
    const paramsToDelete: string[] = [];
    parsed.searchParams.forEach((_, key) => {
      const lowerKey = key.toLowerCase();
      if (
        lowerKey.startsWith("utm_") ||
        lowerKey === "fbclid" ||
        lowerKey === "gclid" ||
        lowerKey === "ref" ||
        lowerKey === "source"
      ) {
        paramsToDelete.push(key);
      }
    });
    for (const key of paramsToDelete) {
      parsed.searchParams.delete(key);
    }

    // Standardize path: remove trailing slash unless root "/"
    let path = parsed.pathname;
    if (path.length > 1 && path.endsWith("/")) {
      path = path.slice(0, -1);
    }
    parsed.pathname = path;

    // Sort remaining query parameters deterministically by (key, value) lexicographically
    const entries = Array.from(parsed.searchParams.entries());
    entries.sort((a, b) => {
      if (a[0] !== b[0]) return a[0] < b[0] ? -1 : 1;
      return a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0;
    });
    const sortedParams = new URLSearchParams();
    for (const [k, v] of entries) {
      sortedParams.append(k, v);
    }

    // Reconstruct URL
    const query = sortedParams.toString();
    const normalized = `${parsed.protocol}//${parsed.host}${parsed.pathname}${
      query ? `?${query}` : ""
    }${parsed.hash ? parsed.hash : ""}`;

    return normalized;
  } catch {
    // If invalid URL, fallback to trimmed lowercase
    return trimmed.toLowerCase();
  }
}

/**
 * Normalizes title text by applying Unicode NFC normalization, collapsing multiple whitespaces, and trimming.
 */
export function normalizeTitle(title: string): string {
  return title.normalize("NFC").trim().replace(/\s+/g, " ");
}

/**
 * Computes raw SHA-256 hex digest of binary data (Buffer or Uint8Array).
 */
export function computeRawImageHash(imageBytes: Buffer | Uint8Array): string {
  return crypto.createHash("sha256").update(imageBytes).digest("hex").toLowerCase();
}

/**
 * Deterministic RFC 8785 canonical JSON serializer for provenance metadata.
 * Ensures strict lexicographical key ordering and no whitespace between tokens.
 */
export function buildCanonicalMetadata(
  imageSha256: string,
  sourceUrl: string,
  title: string,
  timestamp: number
): string {
  const payload: Record<string, string | number> = {
    image_sha256: imageSha256.toLowerCase().replace(/^0x/, ""),
    source_url: normalizeUrl(sourceUrl),
    timestamp: Math.floor(timestamp),
    title: normalizeTitle(title),
  };

  const sortedKeys = Object.keys(payload).sort();
  const serializedEntries = sortedKeys.map(
    (key) => `${JSON.stringify(key)}:${JSON.stringify(payload[key])}`
  );

  return `{${serializedEntries.join(",")}}`;
}

/**
 * Generates composite two-tier provenance fingerprint for EVM notarization.
 * 
 * @param imageBytes Raw image buffer or Uint8Array
 * @param sourceUrl Discovered source candidate URL
 * @param title Metadata title or source reference
 * @param timestamp Epoch timestamp in seconds
 * @returns Object containing EVM bytes32 hex ("0x..."), canonical JSON, image SHA256, and raw 32-byte Buffer
 */
export function generateCompositeFingerprint(
  imageBytes: Buffer | Uint8Array,
  sourceUrl: string,
  title: string,
  timestamp: number
): {
  bytes32Hex: string;
  canonicalJson: string;
  imageSha256: string;
  rawDigest: Buffer;
} {
  const imageSha256 = computeRawImageHash(imageBytes);
  const canonicalJson = buildCanonicalMetadata(imageSha256, sourceUrl, title, timestamp);
  const rawDigest = crypto.createHash("sha256").update(Buffer.from(canonicalJson, "utf-8")).digest();
  const bytes32Hex = `0x${rawDigest.toString("hex").toLowerCase()}`;

  return {
    bytes32Hex,
    canonicalJson,
    imageSha256,
    rawDigest,
  };
}

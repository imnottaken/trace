const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface FaceResult {
  face_detected: boolean;
  face_count: number;
  bounding_box: number[] | null;
  confidence: number;
  warning: string | null;
  faces: Array<{
    bbox: number[];
    confidence: number;
    is_primary: boolean;
  }>;
}

export interface SearchMatch {
  source_url: string;
  page_title: string;
  image_url: string | null;
  thumbnail_url: string | null;
  domain: string;
  snippet: string;
  similarity_score: number;
  calibrated_score: number;
  face_detected: boolean;
  is_social?: boolean;
  image_hash: string;
}

export interface SearchResponse {
  success: boolean;
  error?: string;
  face_analysis: {
    face_detected: boolean;
    face_count: number;
    confidence: number;
    bounding_box: number[] | null;
    warning: string | null;
  };
  search_provider: string;
  candidates_found: number;
  matches: SearchMatch[];
  best_match: SearchMatch | null;
}

export interface ProofResult {
  success: boolean;
  tx_hash: string;
  block_number: number;
  timestamp: number;
  gas_used: number;
  network: string;
  chain_id: number;
  contract_address: string;
  status: string;
}

export interface VerifyResult {
  success: boolean;
  exists: boolean;
  timestamp: number;
  content_hash: string;
  network: string;
  verified: boolean;
}

export interface TamperResult {
  success: boolean;
  local_hash: string;
  on_chain_hash: string;
  on_chain_exists: boolean;
  on_chain_timestamp: number;
  hashes_match: boolean;
  tampered: boolean;
  status: string;
  network: string;
}

export interface TraceStep {
  step: string;
  status: string;
  duration_s?: number;
  [key: string]: unknown;
}

export interface TraceResult {
  success: boolean;
  error?: string;
  steps: TraceStep[];
  result?: {
    face_analysis: {
      face_detected: boolean;
      face_count: number;
      confidence: number;
      bounding_box: number[] | null;
    };
    best_match: SearchMatch;
    all_matches: SearchMatch[];
    fingerprint: {
      content_hash: string;
      image_sha256: string;
      timestamp: number;
    };
    blockchain: {
      tx_hash: string;
      block_number: number;
      timestamp: number;
      gas_used: number;
      network: string;
      chain_id: number;
      contract_address: string;
      status: string;
    } | null;
    verification: {
      exists: boolean;
      timestamp: number;
      content_hash: string;
      network: string;
    } | null;
    search_provider: string;
  };
}

export async function analyzeFace(file: File): Promise<FaceResult> {
  const formData = new FormData();
  formData.append("image", file);
  const res = await fetch(`${API_URL}/api/analyze-face`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Face analysis failed" }));
    throw new Error(err.detail || "Face analysis failed");
  }
  return res.json();
}

export async function searchAndMatch(file: File): Promise<SearchResponse> {
  const formData = new FormData();
  formData.append("image", file);
  const res = await fetch(`${API_URL}/api/search`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Search failed" }));
    throw new Error(err.detail || "Search failed");
  }
  return res.json();
}

export async function registerProof(
  contentHash: string,
  sourceReference: string
): Promise<ProofResult> {
  const res = await fetch(`${API_URL}/api/register-proof`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content_hash: contentHash,
      source_reference: sourceReference,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration failed" }));
    throw new Error(err.detail || "Registration failed");
  }
  return res.json();
}

export async function verifyProof(contentHash: string): Promise<VerifyResult> {
  const res = await fetch(`${API_URL}/api/verify-proof`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content_hash: contentHash }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Verification failed" }));
    throw new Error(err.detail || "Verification failed");
  }
  return res.json();
}

export async function tamperCheck(
  file: File,
  contentHash: string
): Promise<TamperResult> {
  const formData = new FormData();
  formData.append("image", file);
  formData.append("content_hash", contentHash);
  const res = await fetch(`${API_URL}/api/tamper-check`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Tamper check failed" }));
    throw new Error(err.detail || "Tamper check failed");
  }
  return res.json();
}

export async function runFullTrace(file: File): Promise<TraceResult> {
  const formData = new FormData();
  formData.append("image", file);
  const res = await fetch(`${API_URL}/api/trace`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Trace pipeline failed" }));
    throw new Error(err.detail || "Trace pipeline failed");
  }
  return res.json();
}

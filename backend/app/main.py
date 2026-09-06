"""
TRACE — FastAPI Backend Application
Face Identification & Blockchain Verification Pipeline

Endpoints:
  POST /api/analyze-face     — Detect face and generate embedding
  POST /api/search           — Reverse image search + face matching
  POST /api/register-proof   — Register content hash on blockchain
  POST /api/verify-proof     — Verify content hash against blockchain
  POST /api/tamper-check     — Upload file, compute hash, compare to on-chain
  POST /api/trace            — Full pipeline: detect → search → match → fingerprint → register
  GET  /api/health           — Health check
"""

import hashlib
import io
import logging
import os
import time
import traceback
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
load_dotenv()

from backend.app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("trace.api")

app = FastAPI(
    title="TRACE API",
    description="चेहरा → सबूत — Face Identification & Blockchain Verification",
    version="1.0.0",
)

# CORS — allow all origins for hackathon prototype
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---


class RegisterProofRequest(BaseModel):
    content_hash: str
    source_reference: str


class VerifyProofRequest(BaseModel):
    content_hash: str


# --- Lazy initialization ---

_face_engine = None
_search_provider = None
_blockchain_service = None


def get_face_engine():
    global _face_engine
    if _face_engine is None:
        from backend.app.ml.face_engine import FaceEngine

        settings = get_settings()
        _face_engine = FaceEngine(
            model_name=settings.FACE_MODEL,
            det_thresh=settings.FACE_DET_THRESH,
        )
    return _face_engine


def get_search_provider():
    global _search_provider
    if _search_provider is None:
        from backend.app.search.providers import get_search_provider as _get_sp

        settings = get_settings()
        api_key = settings.SERPAPI_API_KEY or os.getenv("SERPAPI_API_KEY", "")
        _search_provider = _get_sp(
            provider_name=settings.SEARCH_PROVIDER,
            api_key=api_key,
        )
    return _search_provider


def get_blockchain():
    global _blockchain_service
    if _blockchain_service is None:
        from backend.app.blockchain.chain_service import BlockchainService

        settings = get_settings()
        if settings.CONTRACT_ADDRESS:
            _blockchain_service = BlockchainService(
                rpc_url=settings.BLOCKCHAIN_RPC_URL,
                private_key=settings.EVM_PRIVATE_KEY,
                contract_address=settings.CONTRACT_ADDRESS,
                chain_id=settings.CHAIN_ID,
            )
        else:
            logger.warning("CONTRACT_ADDRESS not set — blockchain features disabled")
    return _blockchain_service


# --- Health ---


@app.get("/api/health")
async def health():
    settings = get_settings()
    bc = get_blockchain()
    return {
        "status": "ok",
        "service": "TRACE API",
        "search_provider": settings.SEARCH_PROVIDER,
        "blockchain_connected": bc.is_connected if bc else False,
        "blockchain_network": bc.network_name if bc else "not configured",
        "contract_address": settings.CONTRACT_ADDRESS or "not deployed",
    }


# --- Face Analysis ---


@app.post("/api/analyze-face")
async def analyze_face(image: UploadFile = File(...)):
    """Detect face(s) in uploaded image and return analysis."""
    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty image file")

        engine = get_face_engine()
        result = engine.analyze_face(image_bytes)

        # Strip raw embedding from response (security)
        response = {
            "face_detected": result["face_detected"],
            "face_count": result["face_count"],
            "bounding_box": result["bounding_box"],
            "confidence": result["confidence"],
            "warning": result["warning"],
            "faces": result["faces"],
        }

        return JSONResponse(content=response)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Face analysis failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Face analysis failed: {str(e)}")


# --- Search & Match ---


@app.post("/api/search")
async def search_and_match(image: UploadFile = File(...)):
    """Run reverse image search and face-match candidates."""
    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty image file")

        engine = get_face_engine()
        settings = get_settings()

        # Step 1: Detect face and extract embedding
        logger.info("Step 1: Analyzing face...")
        analysis = engine.analyze_face(image_bytes)
        if not analysis["face_detected"]:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "No face detected in uploaded image",
                    "face_analysis": {
                        "face_detected": False,
                        "face_count": 0,
                    },
                    "candidates": [],
                },
                status_code=200,
            )

        embedding = engine.extract_embedding(image_bytes)

        # Step 2: Run reverse image search
        logger.info("Step 2: Running reverse image search...")
        provider = get_search_provider()
        search_results = await provider.search(
            image_bytes, max_results=settings.MAX_SEARCH_CANDIDATES
        )

        if not search_results:
            return JSONResponse(
                content={
                    "success": True,
                    "face_analysis": {
                        "face_detected": True,
                        "face_count": analysis["face_count"],
                        "confidence": analysis["confidence"],
                        "warning": analysis["warning"],
                    },
                    "search_provider": provider.name,
                    "candidates_found": 0,
                    "candidates": [],
                    "message": "No search results found for this image",
                },
            )

        # Step 3: Match candidates
        logger.info("Step 3: Matching %d candidates...", len(search_results))
        from backend.app.search.candidate_matcher import match_candidates

        matched = await match_candidates(
            input_embedding=embedding,
            candidates=search_results,
            face_engine=engine,
            similarity_threshold=settings.SIMILARITY_THRESHOLD,
        )

        return JSONResponse(
            content={
                "success": True,
                "face_analysis": {
                    "face_detected": True,
                    "face_count": analysis["face_count"],
                    "confidence": analysis["confidence"],
                    "bounding_box": analysis["bounding_box"],
                    "warning": analysis["warning"],
                },
                "search_provider": provider.name,
                "candidates_found": len(search_results),
                "matches": [m.to_dict() for m in matched],
                "best_match": matched[0].to_dict() if matched else None,
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Search failed: %s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# --- Register Proof ---


@app.post("/api/register-proof")
async def register_proof(request: RegisterProofRequest):
    """Register content hash on blockchain."""
    try:
        bc = get_blockchain()
        if bc is None:
            raise HTTPException(
                status_code=503,
                detail="Blockchain service not configured. Set CONTRACT_ADDRESS in .env",
            )

        result = bc.record_evidence(
            content_hash_hex=request.content_hash,
            source_reference=request.source_reference,
        )

        return JSONResponse(
            content={
                "success": True,
                "tx_hash": result["tx_hash"],
                "block_number": result["block_number"],
                "timestamp": result["timestamp"],
                "gas_used": result["gas_used"],
                "network": result["network"],
                "chain_id": result["chain_id"],
                "contract_address": result["contract_address"],
                "status": result["status"],
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Proof registration failed: %s", traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Blockchain registration failed: {str(e)}"
        )


# --- Verify Proof ---


@app.post("/api/verify-proof")
async def verify_proof(request: VerifyProofRequest):
    """Verify content hash against blockchain record."""
    try:
        bc = get_blockchain()
        if bc is None:
            raise HTTPException(
                status_code=503,
                detail="Blockchain service not configured. Set CONTRACT_ADDRESS in .env",
            )

        result = bc.verify_evidence(content_hash_hex=request.content_hash)

        return JSONResponse(
            content={
                "success": True,
                "exists": result["exists"],
                "timestamp": result["timestamp"],
                "content_hash": result["content_hash"],
                "network": result["network"],
                "verified": result["exists"],
            },
        )

    except Exception as e:
        logger.error("Verification failed: %s", traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Blockchain verification failed: {str(e)}"
        )


# --- Tamper Check ---


@app.post("/api/tamper-check")
async def tamper_check(
    image: UploadFile = File(...),
    content_hash: str = Form(...),
):
    """
    Upload a file, compute its SHA-256, and compare to an on-chain hash.
    Used to demonstrate tamper detection.
    """
    try:
        file_bytes = await image.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file")

        # Compute local hash
        local_hash = hashlib.sha256(file_bytes).hexdigest()

        # Query blockchain
        bc = get_blockchain()
        if bc is None:
            raise HTTPException(
                status_code=503,
                detail="Blockchain service not configured",
            )

        # Verify the provided content_hash on-chain
        on_chain = bc.verify_evidence(content_hash_hex=content_hash)

        # Compare the local file hash to see if content matches
        # The content_hash on-chain is a composite hash, so we compare directly
        local_content_hash = "0x" + local_hash
        hashes_match = local_content_hash.lower() == content_hash.lower()

        return JSONResponse(
            content={
                "success": True,
                "local_hash": local_content_hash,
                "on_chain_hash": content_hash,
                "on_chain_exists": on_chain["exists"],
                "on_chain_timestamp": on_chain["timestamp"],
                "hashes_match": hashes_match,
                "tampered": not hashes_match,
                "status": "VERIFIED" if hashes_match else "CONTENT MODIFIED",
                "network": on_chain["network"],
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Tamper check failed: %s", traceback.format_exc())
        raise HTTPException(
            status_code=500, detail=f"Tamper check failed: {str(e)}"
        )


# --- Full Trace Pipeline ---


@app.post("/api/trace")
async def full_trace(image: UploadFile = File(...)):
    """
    Full TRACE pipeline:
    1. Face Detection & Embedding
    2. Reverse Image Search
    3. Candidate Face Matching
    4. Content Fingerprinting
    5. Blockchain Registration
    """
    steps = []
    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Empty image file")

        engine = get_face_engine()
        settings = get_settings()

        # === STEP 1: Face Analysis ===
        logger.info("TRACE Step 1: Face Analysis")
        t0 = time.time()
        analysis = engine.analyze_face(image_bytes)
        step1_time = round(time.time() - t0, 2)

        steps.append({
            "step": "face_analysis",
            "status": "complete" if analysis["face_detected"] else "failed",
            "duration_s": step1_time,
            "face_detected": analysis["face_detected"],
            "face_count": analysis["face_count"],
            "confidence": analysis["confidence"],
            "bounding_box": analysis["bounding_box"],
            "warning": analysis["warning"],
        })

        if not analysis["face_detected"]:
            return JSONResponse(content={
                "success": False,
                "error": "No face detected in uploaded image",
                "steps": steps,
            })

        embedding = engine.extract_embedding(image_bytes)

        # === STEP 2: Web Search ===
        logger.info("TRACE Step 2: Web Search")
        t0 = time.time()
        provider = get_search_provider()
        search_results = await provider.search(
            image_bytes, max_results=settings.MAX_SEARCH_CANDIDATES
        )
        step2_time = round(time.time() - t0, 2)

        steps.append({
            "step": "web_search",
            "status": "complete" if search_results else "no_results",
            "duration_s": step2_time,
            "provider": provider.name,
            "candidates_found": len(search_results),
        })

        if not search_results:
            return JSONResponse(content={
                "success": False,
                "event_code": "NO_WEB_MATCHES_INDEXED",
                "error": "No visual occurrences of this image are currently indexed on the public web.",
                "steps": steps,
            })

        # === STEP 3: Candidate Matching ===
        logger.info("TRACE Step 3: Candidate Matching")
        t0 = time.time()
        from backend.app.search.candidate_matcher import match_candidates_with_stats

        matched, stats = await match_candidates_with_stats(
            input_embedding=embedding,
            candidates=search_results,
            face_engine=engine,
            similarity_threshold=settings.SIMILARITY_THRESHOLD,
        )
        step3_time = round(time.time() - t0, 2)

        best_match = matched[0] if matched else None
        steps.append({
            "step": "candidate_matching",
            "status": "complete" if best_match else "failed",
            "duration_s": step3_time,
            "total_matched": len(matched),
            "safe_candidates": stats["safe_candidates_count"],
            "blocked_nsfw": stats["blocked_nsfw_count"],
            "event_code": stats["event_code"],
            "best_similarity": round(best_match.similarity_score, 4) if best_match else 0,
        })

        if not best_match:
            return JSONResponse(content={
                "success": False,
                "event_code": stats["event_code"],
                "error": stats["event_message"] or "No matching face found in verified search candidates.",
                "steps": steps,
                "stats": stats,
                "candidates_evaluated": len(search_results),
            })

        # === STEP 4: Content Fingerprint ===
        logger.info("TRACE Step 4: Content Fingerprinting")
        t0 = time.time()
        from backend.app.blockchain.fingerprint import generate_composite_fingerprint

        source_image_bytes = best_match.image_bytes or image_bytes
        timestamp = int(time.time())

        bytes32_hex, canonical_json, image_sha256, raw_digest = (
            generate_composite_fingerprint(
                image_bytes=source_image_bytes,
                source_url=best_match.search_result.source_url,
                title=best_match.search_result.page_title,
                timestamp=timestamp,
            )
        )
        step4_time = round(time.time() - t0, 2)

        steps.append({
            "step": "fingerprint",
            "status": "complete",
            "duration_s": step4_time,
            "content_hash": bytes32_hex,
            "image_sha256": image_sha256,
            "timestamp": timestamp,
        })

        # === STEP 5: Blockchain Registration ===
        logger.info("TRACE Step 5: Blockchain Registration")
        bc = get_blockchain()
        blockchain_result = None

        if bc is not None:
            t0 = time.time()
            try:
                blockchain_result = bc.record_evidence(
                    content_hash_hex=bytes32_hex,
                    source_reference=best_match.search_result.source_url,
                )
                step5_time = round(time.time() - t0, 2)
                steps.append({
                    "step": "blockchain_registration",
                    "status": "complete",
                    "duration_s": step5_time,
                    "tx_hash": blockchain_result["tx_hash"],
                    "block_number": blockchain_result["block_number"],
                    "network": blockchain_result["network"],
                    "gas_used": blockchain_result["gas_used"],
                })
            except Exception as e:
                step5_time = round(time.time() - t0, 2)
                logger.error("Blockchain registration failed: %s", e)
                steps.append({
                    "step": "blockchain_registration",
                    "status": "failed",
                    "duration_s": step5_time,
                    "error": str(e),
                })
        else:
            steps.append({
                "step": "blockchain_registration",
                "status": "skipped",
                "reason": "Blockchain not configured",
            })

        # === STEP 6: Verification ===
        verification = None
        if bc is not None and blockchain_result:
            try:
                verification = bc.verify_evidence(content_hash_hex=bytes32_hex)
                steps.append({
                    "step": "verification",
                    "status": "verified" if verification["exists"] else "not_found",
                    "on_chain_exists": verification["exists"],
                    "on_chain_timestamp": verification["timestamp"],
                })
            except Exception as e:
                steps.append({
                    "step": "verification",
                    "status": "failed",
                    "error": str(e),
                })

        # === Final Response ===
        return JSONResponse(content={
            "success": True,
            "steps": steps,
            "result": {
                "face_analysis": {
                    "face_detected": True,
                    "face_count": analysis["face_count"],
                    "confidence": analysis["confidence"],
                    "bounding_box": analysis["bounding_box"],
                },
                "best_match": best_match.to_dict(),
                "all_matches": [m.to_dict() for m in matched[:5]],
                "fingerprint": {
                    "content_hash": bytes32_hex,
                    "image_sha256": image_sha256,
                    "timestamp": timestamp,
                },
                "blockchain": blockchain_result,
                "verification": verification,
                "search_provider": provider.name,
            },
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error("TRACE pipeline failed: %s", traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"TRACE pipeline error: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

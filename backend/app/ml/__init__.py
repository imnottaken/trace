"""
TRACE Face Detection & Embedding ML Package.
InsightFace SCRFD detection & ArcFace embedding extraction.
"""

from backend.app.ml.weights_loader import (
    BUFFALO_SC_URL,
    BUFFALO_L_URL,
    get_model_dir,
    is_model_cached,
    download_and_extract_model,
    ensure_model_available,
)
from backend.app.ml.face_engine import (
    FaceDetection,
    FaceEngine,
    get_face_engine,
    detect_faces,
    analyze_face,
    extract_embedding,
    compute_similarity,
)

__all__ = [
    "BUFFALO_SC_URL",
    "BUFFALO_L_URL",
    "get_model_dir",
    "is_model_cached",
    "download_and_extract_model",
    "ensure_model_available",
    "FaceDetection",
    "FaceEngine",
    "get_face_engine",
    "detect_faces",
    "analyze_face",
    "extract_embedding",
    "compute_similarity",
]

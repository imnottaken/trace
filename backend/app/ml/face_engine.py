"""
Face detection and ArcFace embedding engine powered by InsightFace / ONNX Runtime.
Provides SCRFD face detection, 512-d unit-normalized ArcFace embedding extraction,
single/multi/no-face analysis, and cosine visual similarity computation.
"""

import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

import cv2
import numpy as np
from PIL import Image
from insightface.app import FaceAnalysis

from backend.app.ml.weights_loader import ensure_model_available, get_insightface_root

logger = logging.getLogger("trace.ml.face_engine")


@dataclass
class FaceDetection:
    """Represents a detected face with coordinates, score, landmarks, and embedding."""
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    landmarks: Optional[List[List[float]]] = None  # 5 facial landmarks
    embedding: Optional[np.ndarray] = None  # 512-d float32 unit-normalized vector
    is_primary: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": [round(float(c), 2) for c in self.bbox],
            "confidence": round(float(self.confidence), 4),
            "landmarks": (
                [[round(float(p), 2) for p in pt] for pt in self.landmarks]
                if self.landmarks is not None
                else None
            ),
            "is_primary": bool(self.is_primary),
            "has_embedding": self.embedding is not None,
        }


class FaceEngine:
    """
    TRACE Face Engine wrapping InsightFace SCRFD and ArcFace recognition networks.
    Guarantees thread-safe inference, unit-normalized 512-d vectors, and robust decoding.
    """

    def __init__(
        self,
        model_name: str = "buffalo_sc",
        root_dir: Optional[str] = None,
        providers: Optional[List[str]] = None,
        det_thresh: float = 0.5,
        det_size: Tuple[int, int] = (640, 640),
    ):
        self.model_name = model_name
        self.root_dir = root_dir
        self.det_thresh = det_thresh
        self.det_size = det_size

        if providers is None:
            # CPUExecutionProvider is universally supported and thread-safe
            self.providers = ["CPUExecutionProvider"]
        else:
            self.providers = providers

        # Ensure model weights are downloaded and verified
        active_model, model_path = ensure_model_available(
            primary_model=self.model_name,
            fallback_model="buffalo_l",
            root_dir=self.root_dir,
        )
        self.active_model_name = active_model
        self.model_path = model_path

        base_root = str(get_insightface_root(self.root_dir))
        logger.info(
            "Initializing InsightFace FaceAnalysis (model=%s, root=%s, providers=%s)...",
            self.active_model_name,
            base_root,
            self.providers,
        )

        self.app = FaceAnalysis(
            name=self.active_model_name,
            root=base_root,
            providers=self.providers,
        )
        self.app.prepare(ctx_id=0, det_thresh=self.det_thresh, det_size=self.det_size)
        logger.info("FaceEngine initialized successfully with models: %s", list(self.app.models.keys()))

    def decode_image(self, image_data: Union[bytes, np.ndarray]) -> np.ndarray:
        """
        Decode raw image bytes to an OpenCV BGR uint8 numpy array.
        Handles PNG, JPEG, WebP, BMP, and GIF via OpenCV and Pillow fallbacks.
        """
        if isinstance(image_data, np.ndarray):
            if image_data.size == 0 or (
                image_data.ndim >= 2 and (image_data.shape[0] == 0 or image_data.shape[1] == 0)
            ):
                raise ValueError("Empty image numpy array provided")
            if image_data.ndim == 2:
                return cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)
            elif image_data.ndim == 3:
                channels = image_data.shape[2]
                if channels == 1:
                    return cv2.cvtColor(image_data, cv2.COLOR_GRAY2BGR)
                elif channels == 3:
                    return image_data
                elif channels == 4:
                    return cv2.cvtColor(image_data, cv2.COLOR_BGRA2BGR)
                else:
                    raise ValueError(f"Unsupported number of image channels: {channels}")
            else:
                raise ValueError(f"Unsupported numpy array dimensions: {image_data.shape}")

        if not isinstance(image_data, (bytes, bytearray)):
            raise TypeError(f"Expected bytes or np.ndarray, got {type(image_data)}")

        if len(image_data) == 0:
            raise ValueError("Empty image byte buffer provided")

        # 1. Primary fast decode via OpenCV
        buf = np.frombuffer(image_data, dtype=np.uint8)
        img_bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)

        # 2. Resilient fallback via Pillow
        if img_bgr is None:
            try:
                pil_img = Image.open(io.BytesIO(image_data)).convert("RGB")
                rgb_arr = np.array(pil_img, dtype=np.uint8)
                img_bgr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            except Exception as e:
                raise ValueError(f"Corrupt or unreadable image data: {e}") from e

        if img_bgr is None or img_bgr.size == 0:
            raise ValueError("Failed to decode image data into valid pixel buffer")

        return img_bgr

    def detect_faces(self, image_data: Union[bytes, np.ndarray]) -> List[FaceDetection]:
        """
        Detect all human faces in the image, extract 512-d unit-normalized embeddings,
        rank by bounding box area, and mark the primary face.
        """
        img_bgr = self.decode_image(image_data)
        h, w = img_bgr.shape[:2]

        if h == 0 or w == 0:
            return []

        # Guard against degenerate dimensions and extreme aspect ratios:
        # 1. min(h, w) < 8: SCRFD minimum anchor stride is 8px; faces cannot resolve below 8px.
        # 2. max(h, w) / max(min(h, w), 1) > 100.0: Extreme aspect ratios cannot contain faces.
        # 3. int(min(h, w) * min(self.det_size) / max(h, w)) == 0: Prevents SCRFD integer scale truncation to 0.
        if (
            min(h, w) < 8
            or (max(h, w) / max(min(h, w), 1)) > 100.0
            or int(min(h, w) * min(self.det_size) / max(h, w)) == 0
        ):
            logger.debug("Skipping face detection on degenerate image dimensions (%dx%d)", w, h)
            return []

        try:
            raw_faces = self.app.get(img_bgr)
        except (cv2.error, ZeroDivisionError, ValueError, Exception) as e:
            logger.warning(
                f"SCRFD candidate detection failed gracefully on shape {img_bgr.shape}: {e}"
            )
            return []

        if not raw_faces:
            return []

        # Sort faces descending by bounding box area (width * height)
        def face_area(f) -> float:
            return float((f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

        raw_faces.sort(key=face_area, reverse=True)

        detections: List[FaceDetection] = []
        for idx, f in enumerate(raw_faces):
            # Coordinates
            bbox = [float(f.bbox[0]), float(f.bbox[1]), float(f.bbox[2]), float(f.bbox[3])]
            confidence = float(f.det_score) if hasattr(f, "det_score") else 1.0

            # Landmarks (5 keypoints)
            landmarks: Optional[List[List[float]]] = None
            if hasattr(f, "kps") and f.kps is not None:
                landmarks = [[float(pt[0]), float(pt[1])] for pt in f.kps]

            # 512-d unit-normalized ArcFace embedding
            norm_emb: Optional[np.ndarray] = None
            if hasattr(f, "embedding") and f.embedding is not None:
                raw_emb = f.embedding.astype(np.float32)
                norm = float(np.linalg.norm(raw_emb))
                if norm > 0:
                    norm_emb = raw_emb / norm
                else:
                    norm_emb = raw_emb

            detections.append(
                FaceDetection(
                    bbox=bbox,
                    confidence=confidence,
                    landmarks=landmarks,
                    embedding=norm_emb,
                    is_primary=(idx == 0),
                )
            )

        return detections

    def analyze_face(self, image_data: Union[bytes, np.ndarray]) -> Dict[str, Any]:
        """
        High-level forensic single/multi/no-face analysis pipeline.
        
        Returns:
            Structured dictionary conforming to API schema and forensics specifications:
            - 0 faces: face_detected=False, face_count=0, warning="No face detected in image"
            - 1 face: face_detected=True, face_count=1, warning=None
            - >1 faces: face_detected=True, face_count=N, warning="Multiple faces detected..."
        """
        detections = self.detect_faces(image_data)
        count = len(detections)

        if count == 0:
            return {
                "face_detected": False,
                "face_count": 0,
                "bounding_box": None,
                "confidence": 0.0,
                "embedding": None,
                "embedding_dim": 512,
                "warning": "No face detected in image",
                "faces": [],
            }

        primary = detections[0]
        primary_emb_list = primary.embedding.tolist() if primary.embedding is not None else None

        if count == 1:
            return {
                "face_detected": True,
                "face_count": 1,
                "bounding_box": primary.bbox,
                "confidence": primary.confidence,
                "embedding": primary_emb_list,
                "embedding_dim": 512,
                "warning": None,
                "faces": [d.to_dict() for d in detections],
            }

        # Multiple faces detected (> 1)
        return {
            "face_detected": True,
            "face_count": count,
            "bounding_box": primary.bbox,
            "confidence": primary.confidence,
            "embedding": primary_emb_list,
            "embedding_dim": 512,
            "warning": f"Multiple faces detected ({count}); analyzing primary face",
            "faces": [d.to_dict() for d in detections],
        }

    def extract_embedding(self, image_data: Union[bytes, np.ndarray]) -> np.ndarray:
        """
        Extract unit-normalized 512-dimensional ArcFace embedding for the primary face.
        
        Raises:
            ValueError: If 0 faces are detected or embedding extraction fails.
            
        Returns:
            np.ndarray of shape (512,) and float32 dtype with L2-norm == 1.0 ± 1e-4.
        """
        detections = self.detect_faces(image_data)
        if not detections:
            raise ValueError("No face detected in image")

        primary = detections[0]
        if primary.embedding is None:
            raise ValueError("Unable to extract facial embedding for detected face")

        emb = primary.embedding
        if emb.shape != (512,):
            raise ValueError(f"Expected 512-d embedding vector, got shape {emb.shape}")

        norm = float(np.linalg.norm(emb))
        if not np.isclose(norm, 1.0, atol=1e-4):
            emb = emb / norm

        return emb.astype(np.float32)

    @staticmethod
    def compute_similarity(
        emb1: np.ndarray,
        emb2: np.ndarray,
        raise_on_non_finite: bool = False,
    ) -> Dict[str, float]:
        """
        Compute mathematical cosine similarity and calibrated forensics score.
        
        Formulae:
            cosine_sim = dot(v1, v2) / (norm(v1) * norm(v2))
            calibrated_score = max(0.0, min(100.0, (cosine_sim - 0.2) / 0.8 * 100.0))
            cosine_dist = max(0.0, 1.0 - cosine_sim)
        """
        v1 = np.asarray(emb1, dtype=np.float32).flatten()
        v2 = np.asarray(emb2, dtype=np.float32).flatten()

        if not np.all(np.isfinite(v1)) or not np.all(np.isfinite(v2)):
            if raise_on_non_finite:
                raise ValueError("Embedding vectors must contain finite numerical values (no NaN or Inf)")
            return {
                "cosine_similarity": 0.0,
                "calibrated_score": 0.0,
                "cosine_distance": 1.0,
                "similarity_percentage": 0.0,
            }

        norm1 = float(np.linalg.norm(v1))
        norm2 = float(np.linalg.norm(v2))

        if norm1 == 0.0 or norm2 == 0.0:
            cosine_sim = 0.0
        else:
            cosine_sim = float(np.dot(v1, v2) / (norm1 * norm2))

        if np.isnan(cosine_sim):
            cosine_sim = 0.0

        cosine_sim = max(-1.0, min(1.0, cosine_sim))
        calibrated_score = max(0.0, min(100.0, (cosine_sim - 0.2) / 0.8 * 100.0))
        cosine_dist = max(0.0, 1.0 - cosine_sim)

        return {
            "cosine_similarity": float(cosine_sim),
            "calibrated_score": round(float(calibrated_score), 2),
            "cosine_distance": round(float(cosine_dist), 4),
            "similarity_percentage": round(float(calibrated_score), 2),
        }


# --- Global Singleton Management ---

_GLOBAL_ENGINE: Optional[FaceEngine] = None


def get_face_engine(model_name: str = "buffalo_sc") -> FaceEngine:
    """Return or initialize the singleton FaceEngine instance."""
    global _GLOBAL_ENGINE
    if _GLOBAL_ENGINE is None:
        _GLOBAL_ENGINE = FaceEngine(model_name=model_name)
    return _GLOBAL_ENGINE


def detect_faces(image_bytes: bytes) -> List[FaceDetection]:
    """Convenience module function forwarding to singleton FaceEngine."""
    return get_face_engine().detect_faces(image_bytes)


def analyze_face(image_bytes: bytes) -> Dict[str, Any]:
    """Convenience module function forwarding to singleton FaceEngine."""
    return get_face_engine().analyze_face(image_bytes)


def extract_embedding(image_bytes: bytes) -> np.ndarray:
    """Convenience module function forwarding to singleton FaceEngine."""
    return get_face_engine().extract_embedding(image_bytes)


def compute_similarity(
    emb1: np.ndarray,
    emb2: np.ndarray,
    raise_on_non_finite: bool = False,
) -> Dict[str, float]:
    """Convenience module function forwarding to FaceEngine static method."""
    return FaceEngine.compute_similarity(emb1, emb2, raise_on_non_finite=raise_on_non_finite)

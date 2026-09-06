"""
Unit tests for Milestone 2: Face Detection & ArcFace Embedding Engine.
Tests weights loading, SCRFD face detection, 512-d ArcFace embedding extraction,
single/multi/no-face analysis, cosine similarity calibration, edge cases, and inference latency.
"""

import os
import sys
import time
import pytest
import numpy as np

# Ensure repository root is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.ml.weights_loader import (
    BUFFALO_SC_URL,
    BUFFALO_L_URL,
    get_model_dir,
    is_model_cached,
    ensure_model_available,
    download_and_extract_model,
)
from backend.app.ml.face_engine import (
    FaceEngine,
    FaceDetection,
    get_face_engine,
    detect_faces,
    analyze_face,
    extract_embedding,
    compute_similarity,
)

FIXTURES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures")
)


@pytest.fixture(scope="session")
def face_engine() -> FaceEngine:
    """Session-scoped FaceEngine to avoid repeated model loading across tests."""
    return get_face_engine(model_name="buffalo_sc")


@pytest.fixture
def clean_portrait_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "clean_portrait.png")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def clean_portrait_jpg_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "clean_portrait.jpg")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def multi_face_portrait_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "multi_face_portrait.png")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def multi_face_portrait_jpg_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "multi_face_portrait.jpg")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def non_face_pattern_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "non_face_pattern.png")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def non_face_pattern_jpg_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "non_face_pattern.jpg")
    with open(path, "rb") as f:
        return f.read()


# ==============================================================================
# 1. Weights Loader & Cache Manager Tests
# ==============================================================================
class TestWeightsLoader:
    """Validates model downloading, caching, directory layout, and fallback mechanisms."""

    def test_buffalo_sc_model_cached(self):
        """buffalo_sc model must be present and verified in cache."""
        assert is_model_cached("buffalo_sc") is True

    def test_model_dir_structure(self):
        """Model directory must resolve to ~/.insightface/models/<model_name>."""
        model_dir = get_model_dir("buffalo_sc")
        assert model_dir.name == "buffalo_sc"
        assert (model_dir / "det_500m.onnx").is_file()
        assert (model_dir / "w600k_mbf.onnx").is_file()

    def test_ensure_model_available_returns_active_model(self):
        """ensure_model_available must resolve buffalo_sc and return its directory."""
        name, path = ensure_model_available("buffalo_sc", fallback_model="buffalo_l")
        assert name == "buffalo_sc"
        assert path.is_dir()

    def test_unsupported_model_raises_value_error(self):
        """Requesting an unsupported model name must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported model"):
            download_and_extract_model("non_existent_model_xyz")


# ==============================================================================
# 2. Face Detection & Bounding Box Tests
# ==============================================================================
class TestFaceDetection:
    """Validates SCRFD face detection coordinates, confidence, landmarks, and area ranking."""

    def test_detect_faces_clean_portrait_single_face(self, face_engine, clean_portrait_bytes):
        """Clean portrait must produce exactly 1 face detection."""
        detections = face_engine.detect_faces(clean_portrait_bytes)
        assert len(detections) == 1
        d = detections[0]
        assert isinstance(d, FaceDetection)
        assert d.is_primary is True
        assert d.confidence >= 0.5

    def test_bounding_box_coordinates_valid(self, face_engine, clean_portrait_bytes):
        """Bounding box must have [x1, y1, x2, y2] with x1 < x2 and y1 < y2 within image bounds."""
        detections = face_engine.detect_faces(clean_portrait_bytes)
        bbox = detections[0].bbox
        assert len(bbox) == 4
        x1, y1, x2, y2 = bbox
        assert 0 <= x1 < x2 <= 400
        assert 0 <= y1 < y2 <= 400

    def test_facial_landmarks_present(self, face_engine, clean_portrait_bytes):
        """SCRFD must return 5 facial keypoints for detected face."""
        detections = face_engine.detect_faces(clean_portrait_bytes)
        landmarks = detections[0].landmarks
        assert landmarks is not None
        assert len(landmarks) == 5
        for pt in landmarks:
            assert len(pt) == 2
            assert 0 <= pt[0] <= 400
            assert 0 <= pt[1] <= 400

    def test_detect_faces_multi_face_returns_multiple(self, face_engine, multi_face_portrait_bytes):
        """Multi-face portrait must detect at least 2 faces with exactly 1 primary."""
        detections = face_engine.detect_faces(multi_face_portrait_bytes)
        assert len(detections) == 2
        primaries = [d for d in detections if d.is_primary]
        assert len(primaries) == 1

    def test_detect_faces_non_face_returns_empty(self, face_engine, non_face_pattern_bytes):
        """Geometric pattern without faces must return an empty list."""
        detections = face_engine.detect_faces(non_face_pattern_bytes)
        assert len(detections) == 0


# ==============================================================================
# 3. Analyze Face Forensics Pipeline Tests
# ==============================================================================
class TestAnalyzeFace:
    """Validates single/multi/no-face analysis and response schema contracts."""

    def test_analyze_face_single_face_contract(self, clean_portrait_bytes):
        """Single face image must return face_detected=True, face_count=1, warning=None."""
        res = analyze_face(clean_portrait_bytes)
        assert res["face_detected"] is True
        assert res["face_count"] == 1
        assert res["warning"] is None
        assert res["confidence"] >= 0.5
        assert len(res["bounding_box"]) == 4
        assert res["embedding"] is not None
        assert len(res["embedding"]) == 512
        assert res["embedding_dim"] == 512

    def test_analyze_face_jpeg_format(self, clean_portrait_jpg_bytes):
        """JPEG format clean portrait must decode and analyze identically."""
        res = analyze_face(clean_portrait_jpg_bytes)
        assert res["face_detected"] is True
        assert res["face_count"] == 1
        assert res["warning"] is None

    def test_analyze_face_multi_face_emits_warning(self, multi_face_portrait_bytes):
        """Multi-face image must return face_detected=True, face_count=2, warning present."""
        res = analyze_face(multi_face_portrait_bytes)
        assert res["face_detected"] is True
        assert res["face_count"] == 2
        assert res["warning"] is not None
        assert "Multiple faces detected" in res["warning"]
        assert len(res["embedding"]) == 512

    def test_analyze_face_multi_face_jpeg(self, multi_face_portrait_jpg_bytes):
        """Multi-face JPEG must emit warning and count 2 faces."""
        res = analyze_face(multi_face_portrait_jpg_bytes)
        assert res["face_detected"] is True
        assert res["face_count"] == 2
        assert "Multiple faces detected" in res["warning"]

    def test_analyze_face_no_face_clean_rejection(self, non_face_pattern_bytes):
        """Non-face pattern must be cleanly rejected with face_detected=False and embedding=None."""
        res = analyze_face(non_face_pattern_bytes)
        assert res["face_detected"] is False
        assert res["face_count"] == 0
        assert res["embedding"] is None
        assert res["warning"] == "No face detected in image"

    def test_analyze_face_no_face_jpeg(self, non_face_pattern_jpg_bytes):
        """Non-face JPEG must also be rejected cleanly."""
        res = analyze_face(non_face_pattern_jpg_bytes)
        assert res["face_detected"] is False
        assert res["face_count"] == 0
        assert res["embedding"] is None

    def test_analyze_face_rejects_empty_bytes(self):
        """Empty byte buffer must raise ValueError."""
        with pytest.raises(ValueError, match="Empty image"):
            analyze_face(b"")

    def test_analyze_face_rejects_corrupted_bytes(self):
        """Corrupted image bytes must raise ValueError."""
        with pytest.raises(ValueError, match="Corrupt or unreadable"):
            analyze_face(b"NOT_A_VALID_IMAGE_BYTES_0xDEADBEEF")


# ==============================================================================
# 4. ArcFace 512-d Embedding Extraction Tests
# ==============================================================================
class TestEmbeddingExtraction:
    """Validates 512-d ArcFace embeddings: dimension, unit normalization, dtype, determinism."""

    def test_embedding_dimension_and_dtype(self, clean_portrait_bytes):
        """Extracted embedding must have exact shape (512,) and float32 dtype."""
        emb = extract_embedding(clean_portrait_bytes)
        assert isinstance(emb, np.ndarray)
        assert emb.shape == (512,)
        assert emb.dtype == np.float32

    def test_embedding_unit_normalized(self, clean_portrait_bytes):
        """L2-norm of extracted embedding must equal 1.0 within tolerance 1e-4."""
        emb = extract_embedding(clean_portrait_bytes)
        norm = float(np.linalg.norm(emb))
        assert np.isclose(norm, 1.0, atol=1e-4)

    def test_embedding_contains_no_nan_or_inf(self, clean_portrait_bytes):
        """Embedding must contain zero NaN or Inf entries."""
        emb = extract_embedding(clean_portrait_bytes)
        assert not np.isnan(emb).any()
        assert not np.isinf(emb).any()

    def test_embedding_extraction_deterministic(self, clean_portrait_bytes):
        """Repeated extraction from identical image bytes must yield identical embeddings."""
        emb1 = extract_embedding(clean_portrait_bytes)
        emb2 = extract_embedding(clean_portrait_bytes)
        np.testing.assert_array_equal(emb1, emb2)

    def test_extract_embedding_raises_on_non_face(self, non_face_pattern_bytes):
        """Attempting to extract embedding from a non-face image must raise ValueError."""
        with pytest.raises(ValueError, match="No face detected"):
            extract_embedding(non_face_pattern_bytes)


# ==============================================================================
# 5. Cosine Similarity & Calibration Tests
# ==============================================================================
class TestCosineSimilarity:
    """Validates mathematical cosine similarity, distance, and 0-100% calibration formula."""

    def test_identity_similarity(self, clean_portrait_bytes):
        """Identical embeddings must produce cosine_similarity == 1.0 and calibrated_score == 100.0%."""
        emb = extract_embedding(clean_portrait_bytes)
        sim = compute_similarity(emb, emb)
        assert np.isclose(sim["cosine_similarity"], 1.0, atol=1e-5)
        assert sim["calibrated_score"] == 100.0
        assert sim["cosine_distance"] == 0.0

    def test_different_faces_lower_similarity(self, clean_portrait_bytes, multi_face_portrait_bytes):
        """Embeddings from two different subjects must yield significantly lower similarity."""
        emb1 = extract_embedding(clean_portrait_bytes)
        emb2 = extract_embedding(multi_face_portrait_bytes)
        sim = compute_similarity(emb1, emb2)
        assert sim["cosine_similarity"] < 0.60
        assert sim["calibrated_score"] < 50.0

    def test_orthogonal_vectors_yield_zero_score(self):
        """Orthogonal vectors (cosine_sim = 0.0) fall below the 0.20 match baseline -> calibrated 0.0%."""
        v1 = np.zeros(512, dtype=np.float32)
        v2 = np.zeros(512, dtype=np.float32)
        v1[0] = 1.0
        v2[1] = 1.0
        sim = compute_similarity(v1, v2)
        assert np.isclose(sim["cosine_similarity"], 0.0, atol=1e-5)
        assert sim["calibrated_score"] == 0.0
        assert sim["cosine_distance"] == 1.0

    def test_opposite_vectors_yield_zero_score(self):
        """Opposite vectors (cosine_sim = -1.0) must produce calibrated_score 0.0% and distance 2.0."""
        v1 = np.zeros(512, dtype=np.float32)
        v1[0] = 1.0
        v2 = -v1
        sim = compute_similarity(v1, v2)
        assert np.isclose(sim["cosine_similarity"], -1.0, atol=1e-5)
        assert sim["calibrated_score"] == 0.0
        assert sim["cosine_distance"] == 2.0

    def test_zero_vector_safety(self):
        """Division by zero safety when handling an all-zero vector."""
        v_zero = np.zeros(512, dtype=np.float32)
        v_norm = np.ones(512, dtype=np.float32) / np.sqrt(512)
        sim = compute_similarity(v_zero, v_norm)
        assert sim["cosine_similarity"] == 0.0
        assert sim["calibrated_score"] == 0.0


# ==============================================================================
# 6. Performance & Latency Benchmark
# ==============================================================================
class TestMLPerformance:
    """Verifies that inference execution meets the sub-200ms CPU requirement."""

    def test_inference_latency_sub_200ms_cpu(self, face_engine, clean_portrait_bytes):
        """Single image face detection & embedding extraction must execute in <200ms on CPU."""
        # Warmup run
        face_engine.detect_faces(clean_portrait_bytes)

        latencies = []
        for _ in range(5):
            t0 = time.perf_counter()
            face_engine.detect_faces(clean_portrait_bytes)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        mean_latency = sum(latencies) / len(latencies)
        assert mean_latency < 200.0, f"Mean latency {mean_latency:.2f}ms exceeded 200ms CPU threshold"


# ==============================================================================
# 7. Edge Case Robustness & Vulnerability Mitigations
# ==============================================================================
class TestEdgeCaseRobustness:
    """Verifies robustness against extreme aspect ratios, numpy array shapes, and non-finite vectors."""

    @pytest.mark.parametrize(
        "shape",
        [(10, 10000, 3), (10000, 10, 3), (1, 641, 3), (641, 1, 3)],
        ids=["wide_10000x10", "tall_10x10000", "boundary_1x641", "boundary_641x1"],
    )
    def test_extreme_aspect_ratios_return_zero_faces_without_crash(self, face_engine, shape):
        """Extreme aspect ratios must return 0 faces without OpenCV assertion or resize crash."""
        arr = np.zeros(shape, dtype=np.uint8)
        detections = face_engine.detect_faces(arr)
        assert detections == []
        analysis = face_engine.analyze_face(arr)
        assert analysis["face_detected"] is False
        assert analysis["face_count"] == 0
        assert analysis["warning"] == "No face detected in image"

    def test_single_channel_3d_array_conversion(self, face_engine):
        """Single-channel 3D array (H, W, 1) must convert cleanly to (H, W, 3) BGR."""
        arr_1ch = np.full((120, 120, 1), 128, dtype=np.uint8)
        decoded = face_engine.decode_image(arr_1ch)
        assert decoded.shape == (120, 120, 3)
        assert decoded.dtype == np.uint8
        # detect_faces must not raise broadcast error
        assert face_engine.detect_faces(arr_1ch) == []

    def test_grayscale_2d_array_conversion(self, face_engine):
        """2D grayscale array (H, W) must convert cleanly to (H, W, 3) BGR."""
        arr_2d = np.full((120, 120), 128, dtype=np.uint8)
        decoded = face_engine.decode_image(arr_2d)
        assert decoded.shape == (120, 120, 3)
        assert decoded.dtype == np.uint8
        assert face_engine.detect_faces(arr_2d) == []

    def test_bgra_4channel_array_conversion(self, face_engine):
        """4-channel BGRA array (H, W, 4) must convert cleanly to (H, W, 3) BGR."""
        arr_4ch = np.full((120, 120, 4), 128, dtype=np.uint8)
        decoded = face_engine.decode_image(arr_4ch)
        assert decoded.shape == (120, 120, 3)
        assert decoded.dtype == np.uint8

    @pytest.mark.parametrize(
        "empty_arr",
        [
            np.zeros((0, 0, 3), dtype=np.uint8),
            np.zeros((0, 100, 3), dtype=np.uint8),
            np.zeros((100, 0, 3), dtype=np.uint8),
            np.zeros((0, 0), dtype=np.uint8),
            np.zeros((0, 0, 1), dtype=np.uint8),
            np.zeros((0, 0, 4), dtype=np.uint8),
            np.zeros((0,), dtype=np.uint8),
        ],
        ids=["empty_0x0x3", "empty_0x100x3", "empty_100x0x3", "empty_2d", "empty_1ch", "empty_bgra", "empty_1d"],
    )
    def test_empty_numpy_array_raises_value_error(self, face_engine, empty_arr):
        """Empty numpy arrays must raise ValueError, not ZeroDivisionError or OpenCV crash."""
        with pytest.raises(ValueError, match="Empty image numpy array"):
            face_engine.decode_image(empty_arr)
        with pytest.raises(ValueError, match="Empty image numpy array"):
            face_engine.detect_faces(empty_arr)

    def test_unsupported_channel_counts_raise_value_error(self, face_engine):
        """Arrays with 2 or 5 channels must raise ValueError for unsupported channels."""
        arr_2ch = np.zeros((100, 100, 2), dtype=np.uint8)
        with pytest.raises(ValueError, match="Unsupported number of image channels: 2"):
            face_engine.decode_image(arr_2ch)
        arr_5ch = np.zeros((100, 100, 5), dtype=np.uint8)
        with pytest.raises(ValueError, match="Unsupported number of image channels: 5"):
            face_engine.decode_image(arr_5ch)

    @pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_vectors_return_zero_similarity(self, bad_val):
        """Non-finite vectors (NaN, Inf, -Inf) must return 0.0 similarity and 0.0% calibrated score."""
        v_bad = np.array([bad_val] * 512, dtype=np.float32)
        v_valid = np.zeros(512, dtype=np.float32)
        v_valid[0] = 1.0

        res = compute_similarity(v_bad, v_valid)
        assert res["cosine_similarity"] == 0.0
        assert res["calibrated_score"] == 0.0
        assert res["cosine_distance"] == 1.0
        assert res["similarity_percentage"] == 0.0

        # With raise_on_non_finite=True, must raise ValueError
        with pytest.raises(ValueError, match="Embedding vectors must contain finite numerical values"):
            compute_similarity(v_bad, v_valid, raise_on_non_finite=True)


class TestWeightsLoaderExceptionHandling:
    """Verifies downloader retry handling on http.client network exceptions."""

    def test_retry_on_incomplete_read(self, tmp_path):
        """Downloader must catch http.client.IncompleteRead and retry up to max_retries."""
        import http.client
        from unittest.mock import patch
        from backend.app.ml.weights_loader import download_and_extract_model

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = http.client.IncompleteRead(b"partial", expected=1000)
            with pytest.raises(RuntimeError, match="Failed to download and extract model"):
                download_and_extract_model(
                    "buffalo_sc",
                    root_dir=str(tmp_path),
                    max_retries=3,
                    retry_delay=0.01,
                )
            assert mock_urlopen.call_count == 3

"""
Empirical Challenger 1 Adversarial Stress Test Suite for Milestone 2:
Face Detection & ArcFace Embedding Engine (face_engine.py).

Adversarial Stress Test Matrix:
1. Truncated and corrupted image byte payloads:
   - Empty buffer (zero bytes)
   - Corrupt/incomplete headers (PNG, JPEG, WebP, GIF)
   - Randomized noise byte payloads (1B, 100B, 10KB, 1MB)
   - Non-image file headers (PDF, HTML, shell script, ELF binary, ZIP)
   - Systematic fractional truncations (1% to 99% of valid PNG/JPEG streams)
2. Massive resolution images:
   - 4000x4000 solid color canvas (graceful non-detection without memory explosion)
   - 4000x4000 with real human portrait embedded (accurate detection and 512-d embedding)
   - 8000x8000 high-resolution canvas stress test
3. Extreme aspect ratios:
   - 10000x10 (ultra-wide) and 10x10000 (ultra-tall)
   - Aspect ratio boundaries: 1x641, 641x1, 1x1000, 1000x1
   - Degenerate dimensions: 1x1, 2x2, empty numpy array (0, 0, 3)
   - Crash/segfault resistance: OpenCV resize inv_scale assertions and ZeroDivisionError
4. Synthetic patterns, pure noise, and solid colors:
   - Uniform random RGB noise (640x640)
   - Solid colors: black, white, green, gray (640x640)
   - Synthetic high-frequency checkerboard pattern
   - Gaussian distributed noise
   - Clean non-detection and rejection in extract_embedding
5. Multi-face scaling and primary selection:
   - 6-face collage of varying sizes
   - 10-face grid collage
   - Strict area-descending sort order verification
   - Single primary face selection (is_primary == True on index 0 only)
   - Forensics warning message format compliance
6. Adversarial embedding vector security:
   - NaN and Inf vector injection in compute_similarity
   - Verification against 100% false positive match collapse
"""

import io
import os
import sys
import time
import pytest
import numpy as np
import cv2
from PIL import Image

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backend.app.ml.face_engine import (
    FaceEngine,
    FaceDetection,
    get_face_engine,
    detect_faces,
    analyze_face,
    extract_embedding,
    compute_similarity,
)

FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")


@pytest.fixture(scope="session")
def engine() -> FaceEngine:
    """Session-scoped FaceEngine to avoid repeated model loading."""
    return get_face_engine(model_name="buffalo_sc")


@pytest.fixture(scope="session")
def clean_portrait_png() -> bytes:
    path = os.path.join(FIXTURES_DIR, "clean_portrait.png")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def clean_portrait_jpg() -> bytes:
    path = os.path.join(FIXTURES_DIR, "clean_portrait.jpg")
    with open(path, "rb") as f:
        return f.read()


# ==============================================================================
# 1. Truncated & Corrupted Image Byte Payloads
# ==============================================================================
class TestCorruptedAndTruncatedImages:
    """Stress tests face_engine with zero-byte, truncated, corrupted, and invalid payloads."""

    def test_zero_byte_input_rejected_cleanly(self, engine):
        """Zero-byte image buffer must raise ValueError and not crash."""
        with pytest.raises(ValueError, match="Empty image"):
            engine.decode_image(b"")

        with pytest.raises(ValueError, match="Empty image"):
            engine.detect_faces(b"")

        with pytest.raises(ValueError, match="Empty image"):
            engine.analyze_face(b"")

        with pytest.raises(ValueError, match="Empty image"):
            engine.extract_embedding(b"")

    @pytest.mark.parametrize(
        "corrupt_header",
        [
            b"\x00",
            b"\x00" * 256,
            b"GIF89a",
            b"\xff\xd8\xff\xe0\x00\x10JFIF",
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
            b"RIFF\x00\x00\x00\x00WEBPVP8 ",
            b"BM\x00\x00\x00\x00\x00\x00\x00\x00",
        ],
        ids=["single_null", "null_stream", "trunc_gif", "trunc_jpeg", "trunc_png", "trunc_webp", "trunc_bmp"]
    )
    def test_corrupt_headers_raise_value_error(self, engine, corrupt_header):
        """Truncated headers missing image body must raise ValueError."""
        with pytest.raises(ValueError, match="Corrupt or unreadable"):
            engine.analyze_face(corrupt_header)

    @pytest.mark.parametrize("size", [1, 16, 256, 4096, 65536])
    def test_random_bytes_raise_value_error(self, engine, size):
        """Pseudo-random byte payloads of various sizes must raise ValueError."""
        np.random.seed(size)
        random_payload = np.random.bytes(size)
        with pytest.raises(ValueError, match="Corrupt or unreadable"):
            engine.analyze_face(random_payload)

    @pytest.mark.parametrize(
        "non_image_payload,label",
        [
            (b"%PDF-1.7\n%Fake PDF binary\n%%EOF", "pdf"),
            (b"<!DOCTYPE html><html><body><h1>Not an image</h1></body></html>", "html"),
            (b"#!/usr/bin/env bash\necho 'exploit'\nexit 1", "shell_script"),
            (b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 32, "elf_binary"),
            (b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"\x00" * 32, "zip_archive"),
        ]
    )
    def test_non_image_file_types_raise_value_error(self, engine, non_image_payload, label):
        """Non-image binary/text files masquerading as images must be safely rejected."""
        with pytest.raises(ValueError, match="Corrupt or unreadable"):
            engine.analyze_face(non_image_payload)

    def test_systematic_fractional_truncation_png(self, engine, clean_portrait_png):
        """Systematically truncating a valid PNG from 1% to 99% must never segfault or crash."""
        total_len = len(clean_portrait_png)
        for frac in [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99]:
            cut = max(1, int(total_len * frac))
            chunk = clean_portrait_png[:cut]
            try:
                res = engine.analyze_face(chunk)
                assert isinstance(res, dict)
            except ValueError:
                pass  # Graceful rejection of truncated image is expected

    def test_systematic_fractional_truncation_jpeg(self, engine, clean_portrait_jpg):
        """Systematically truncating a valid JPEG from 1% to 99% must never segfault or crash."""
        total_len = len(clean_portrait_jpg)
        for frac in [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.99]:
            cut = max(1, int(total_len * frac))
            chunk = clean_portrait_jpg[:cut]
            try:
                res = engine.analyze_face(chunk)
                assert isinstance(res, dict)
            except ValueError:
                pass  # Graceful rejection of truncated image is expected


# ==============================================================================
# 2. Massive Resolution Images
# ==============================================================================
class TestMassiveResolutionImages:
    """Stress tests massive image resolutions up to 4000x4000 and 8000x8000."""

    def test_massive_4000x4000_solid_color(self, engine):
        """4000x4000 solid image must execute without memory exhaustion or crash."""
        img = np.full((4000, 4000, 3), 128, dtype=np.uint8)
        success, enc = cv2.imencode(".jpg", img)
        assert success

        res = engine.analyze_face(enc.tobytes())
        assert res["face_detected"] is False
        assert res["face_count"] == 0
        assert res["embedding"] is None

    def test_massive_4000x4000_with_embedded_portrait(self, engine, clean_portrait_png):
        """4000x4000 image with a real portrait embedded must detect face and extract embedding."""
        clean_arr = cv2.imdecode(np.frombuffer(clean_portrait_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        ch, cw, _ = clean_arr.shape

        canvas = np.full((4000, 4000, 3), 200, dtype=np.uint8)
        canvas[1200:1200 + ch, 1500:1500 + cw] = clean_arr
        success, enc = cv2.imencode(".jpg", canvas)
        assert success

        res = engine.analyze_face(enc.tobytes())
        assert res["face_detected"] is True
        assert res["face_count"] == 1
        assert res["confidence"] >= 0.5
        assert len(res["embedding"]) == 512
        # Check bounding box falls inside the embedded region
        bbox = res["bounding_box"]
        assert 1400 <= bbox[0] < bbox[2] <= 2000
        assert 1100 <= bbox[1] < bbox[3] <= 1700

    def test_massive_8000x8000_resolution_safety(self, engine):
        """8000x8000 image (~192MB raw buffer) must process safely without crash."""
        img = np.full((8000, 8000, 3), 80, dtype=np.uint8)
        success, enc = cv2.imencode(".jpg", img)
        assert success

        res = engine.analyze_face(enc.tobytes())
        assert res["face_detected"] is False
        assert res["face_count"] == 0


# ==============================================================================
# 3. Extreme Aspect Ratios & Boundary Tests
# ==============================================================================
class TestExtremeAspectRatios:
    """Stress tests extreme aspect ratios (10000x10, 10x10000) and boundary shapes."""

    def test_extreme_aspect_ratio_wide_10000x10(self, engine):
        """10000x10 image must not crash with OpenCV resize assertion failure."""
        img_wide = np.zeros((10, 10000, 3), dtype=np.uint8)
        success, enc = cv2.imencode(".png", img_wide)
        assert success

        try:
            res = engine.analyze_face(enc.tobytes())
            assert res["face_detected"] is False
            assert res["face_count"] == 0
        except ValueError:
            pass
        except cv2.error as e:
            pytest.fail(f"Unhandled OpenCV crash on 10000x10 image: {e}")

    def test_extreme_aspect_ratio_tall_10x10000(self, engine):
        """10x10000 image must not crash with OpenCV resize assertion failure."""
        img_tall = np.zeros((10000, 10, 3), dtype=np.uint8)
        success, enc = cv2.imencode(".png", img_tall)
        assert success

        try:
            res = engine.analyze_face(enc.tobytes())
            assert res["face_detected"] is False
            assert res["face_count"] == 0
        except ValueError:
            pass
        except cv2.error as e:
            pytest.fail(f"Unhandled OpenCV crash on 10x10000 image: {e}")

    @pytest.mark.parametrize("shape", [(1, 641, 3), (641, 1, 3), (1, 1000, 3), (1000, 1, 3)])
    def test_extreme_aspect_ratio_boundaries(self, engine, shape):
        """Boundary shapes exceeding 640:1 ratio must not crash with cv2.error."""
        img = np.zeros(shape, dtype=np.uint8)
        success, enc = cv2.imencode(".png", img)
        assert success

        try:
            res = engine.analyze_face(enc.tobytes())
            assert res["face_detected"] is False
        except ValueError:
            pass
        except cv2.error as e:
            pytest.fail(f"Unhandled OpenCV crash on shape {shape}: {e}")

    def test_degenerate_tiny_images(self, engine):
        """1x1 and 2x2 images must not cause division by zero or crash."""
        for dim in [1, 2, 5, 10]:
            img = np.zeros((dim, dim, 3), dtype=np.uint8)
            success, enc = cv2.imencode(".png", img)
            assert success
            res = engine.analyze_face(enc.tobytes())
            assert res["face_detected"] is False
            assert res["face_count"] == 0

    def test_empty_numpy_array_input(self, engine):
        """Passing an empty numpy array (0, 0, 3) must raise ValueError, not ZeroDivisionError."""
        empty_arr = np.zeros((0, 0, 3), dtype=np.uint8)
        try:
            engine.detect_faces(empty_arr)
            pytest.fail("Expected ValueError on empty numpy array")
        except ValueError:
            pass
        except ZeroDivisionError as e:
            pytest.fail(f"Unhandled ZeroDivisionError on empty numpy array: {e}")


# ==============================================================================
# 4. Synthetic Noise, Solid Colors, and Checkerboard
# ==============================================================================
class TestSyntheticAndNoiseImages:
    """Stress tests synthetic noise, solid colors, and high-frequency patterns."""

    def test_uniform_random_noise_image(self, engine):
        """640x640 uniform random RGB noise must detect 0 faces cleanly."""
        np.random.seed(42)
        noise = np.random.randint(0, 256, (640, 640, 3), dtype=np.uint8)
        success, enc = cv2.imencode(".png", noise)
        assert success

        res = engine.analyze_face(enc.tobytes())
        assert res["face_detected"] is False
        assert res["face_count"] == 0
        assert res["warning"] == "No face detected in image"

    @pytest.mark.parametrize(
        "color",
        [(0, 0, 0), (255, 255, 255), (0, 255, 0), (255, 0, 0), (0, 0, 255), (128, 128, 128)],
        ids=["black", "white", "green", "blue", "red", "gray"]
    )
    def test_solid_color_images(self, engine, color):
        """Solid color images across primary and neutral colors must return 0 faces."""
        img = np.full((640, 640, 3), color, dtype=np.uint8)
        success, enc = cv2.imencode(".png", img)
        assert success

        res = engine.analyze_face(enc.tobytes())
        assert res["face_detected"] is False
        assert res["face_count"] == 0

    def test_synthetic_checkerboard_pattern(self, engine):
        """High-frequency alternating 16x16 checkerboard must return 0 faces."""
        cb = np.zeros((640, 640, 3), dtype=np.uint8)
        for y in range(0, 640, 16):
            for x in range(0, 640, 16):
                if (y // 16 + x // 16) % 2 == 0:
                    cb[y:y + 16, x:x + 16] = 255
        success, enc = cv2.imencode(".png", cb)
        assert success

        res = engine.analyze_face(enc.tobytes())
        assert res["face_detected"] is False
        assert res["face_count"] == 0

    def test_gaussian_noise_image(self, engine):
        """Gaussian distributed noise must return 0 faces."""
        np.random.seed(123)
        gauss = np.random.normal(128, 40, (640, 640, 3)).clip(0, 255).astype(np.uint8)
        success, enc = cv2.imencode(".png", gauss)
        assert success

        res = engine.analyze_face(enc.tobytes())
        assert res["face_detected"] is False
        assert res["face_count"] == 0

    def test_extract_embedding_on_synthetic_raises_value_error(self, engine):
        """extract_embedding on synthetic noise must raise ValueError."""
        solid = np.full((640, 640, 3), 200, dtype=np.uint8)
        success, enc = cv2.imencode(".png", solid)
        assert success

        with pytest.raises(ValueError, match="No face detected"):
            engine.extract_embedding(enc.tobytes())


# ==============================================================================
# 5. Multi-Face Images (5+ Faces Stress Test)
# ==============================================================================
class TestMultiFaceCollageStress:
    """Stress tests detection and primary face selection on images with 5+ faces."""

    def test_6_faces_collage_primary_selection_and_ranking(self, engine, clean_portrait_png):
        """Collage with 6 genuine faces must sort by area descending and pick primary."""
        portrait = cv2.imdecode(np.frombuffer(clean_portrait_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        ph, pw, _ = portrait.shape

        canvas = np.full((1200, 1800, 3), 235, dtype=np.uint8)
        # 6 distinct scales to guarantee distinct bounding box areas
        scales = [1.0, 0.85, 0.70, 0.60, 0.50, 0.40]
        positions = [
            (50, 50),
            (50, 600),
            (50, 1150),
            (650, 50),
            (650, 600),
            (650, 1150),
        ]

        for s, (y, x) in zip(scales, positions):
            resized = cv2.resize(portrait, (int(pw * s), int(ph * s)))
            rh, rw, _ = resized.shape
            canvas[y:y + rh, x:x + rw] = resized

        success, enc = cv2.imencode(".png", canvas)
        assert success
        data = enc.tobytes()

        # 1. Test detect_faces
        detections = engine.detect_faces(data)
        assert len(detections) >= 5, f"Expected at least 5 detections, got {len(detections)}"

        # Verify area descending order
        areas = [(d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]) for d in detections]
        for i in range(len(areas) - 1):
            assert areas[i] >= areas[i + 1], f"Area ranking violated at index {i}: {areas[i]} < {areas[i+1]}"

        # Verify exactly one primary face at index 0
        assert detections[0].is_primary is True
        for d in detections[1:]:
            assert d.is_primary is False

        # 2. Test analyze_face
        analysis = engine.analyze_face(data)
        assert analysis["face_detected"] is True
        assert analysis["face_count"] >= 5
        assert analysis["warning"] == f"Multiple faces detected ({len(detections)}); analyzing primary face"
        assert analysis["embedding"] is not None
        assert len(analysis["embedding"]) == 512
        assert len(analysis["faces"]) == len(detections)

    def test_10_faces_grid_stress(self, engine, clean_portrait_png):
        """Dense 10-face grid must process gracefully without crash or index corruption."""
        portrait = cv2.imdecode(np.frombuffer(clean_portrait_png, dtype=np.uint8), cv2.IMREAD_COLOR)
        ph, pw, _ = portrait.shape

        canvas = np.full((1200, 2500, 3), 240, dtype=np.uint8)
        # 10 faces at varying scales
        scales = [1.1, 0.95, 0.85, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50, 0.45]
        positions = [
            (50, 50), (50, 550), (50, 1050), (50, 1550), (50, 2050),
            (650, 50), (650, 550), (650, 1050), (650, 1550), (650, 2050),
        ]

        for s, (y, x) in zip(scales, positions):
            resized = cv2.resize(portrait, (int(pw * s), int(ph * s)))
            rh, rw, _ = resized.shape
            canvas[y:y + rh, x:x + rw] = resized

        success, enc = cv2.imencode(".png", canvas)
        assert success
        data = enc.tobytes()

        analysis = engine.analyze_face(data)
        assert analysis["face_detected"] is True
        assert analysis["face_count"] >= 8
        assert "Multiple faces detected" in analysis["warning"]
        assert analysis["confidence"] >= 0.5
        assert len(analysis["embedding"]) == 512


# ==============================================================================
# 6. Adversarial Embedding Vector Security
# ==============================================================================
class TestAdversarialVectorSecurity:
    """Stress tests mathematical robustness against NaN/Inf vector injections in similarity."""

    def test_nan_vector_does_not_yield_100_percent_match(self, engine, clean_portrait_png):
        """
        Adversary injecting a NaN-filled vector must NOT achieve a 100% false match.
        min(1.0, float('nan')) evaluating to 1.0 is a known mathematical bypass.
        """
        emb_victim = engine.extract_embedding(clean_portrait_png)
        emb_adversary_nan = np.full(512, np.nan, dtype=np.float32)

        try:
            sim = engine.compute_similarity(emb_victim, emb_adversary_nan)
            # Must not be 100.0% match
            assert sim["calibrated_score"] != 100.0, "Security flaw: NaN vector achieved 100% match!"
            assert sim["cosine_similarity"] != 1.0, "Security flaw: NaN vector achieved cosine_sim 1.0!"
        except ValueError:
            pass  # Raising ValueError on NaN vector is secure and valid

    def test_inf_vector_does_not_yield_100_percent_match(self, engine, clean_portrait_png):
        """Adversary injecting an Inf-filled vector must not achieve a 100% false match."""
        emb_victim = engine.extract_embedding(clean_portrait_png)
        emb_adversary_inf = np.full(512, np.inf, dtype=np.float32)

        try:
            sim = engine.compute_similarity(emb_victim, emb_adversary_inf)
            assert sim["calibrated_score"] != 100.0, "Security flaw: Inf vector achieved 100% match!"
        except ValueError:
            pass  # Raising ValueError on Inf vector is secure and valid


# ==============================================================================
# 7. Process Safety & Integrity Stress
# ==============================================================================
class TestProcessSafetyAndIntegrity:
    """Verifies rapid sequential execution of adversarial inputs causes zero segmentation faults."""

    def test_rapid_sequential_adversarial_executions(self, engine, clean_portrait_png):
        """Execute mixed stream of corrupt, noise, extreme, and valid inputs rapidly."""
        for _ in range(5):
            # 1. Corrupt
            with pytest.raises(ValueError):
                engine.analyze_face(b"DEADBEEF" * 10)
            # 2. Solid color
            solid = np.zeros((200, 200, 3), dtype=np.uint8)
            _, enc_s = cv2.imencode(".png", solid)
            res_s = engine.analyze_face(enc_s.tobytes())
            assert res_s["face_detected"] is False
            # 3. Valid clean portrait
            res_c = engine.analyze_face(clean_portrait_png)
            assert res_c["face_detected"] is True
            assert res_c["face_count"] == 1

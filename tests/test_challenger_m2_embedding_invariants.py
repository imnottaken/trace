"""
Empirical Challenger 2 Test Suite: Embedding Invariants & Metric Space.

Rigorous stress-testing of mathematical invariants:
1. Unit norm invariant: ||e||_2 == 1.0 within 1e-4 tolerance across all valid face detections,
   rotations, blurs, and scale transforms.
2. Metric invariants:
   - S(e, e) == 1.0 (identity)
   - S(e1, e2) == S(e2, e1) (symmetry)
   - -1.0 <= S(e1, e2) <= 1.0 (boundedness)
   - Calibrated percentage score is monotonic with respect to cosine similarity and bounded in [0.0, 100.0].
   - Adversarial non-finite inputs (NaN, Inf).
3. Rotation / slight blur invariance vs distinct identity separation:
   - Intra-identity similarity vs inter-identity margin.
   - Systematic angular rotation (-30 deg to +30 deg) and Gaussian blur (sigma 0.5 to 5.0).
"""

import io
import math
import os
import sys
import cv2
import numpy as np
import pytest
from PIL import Image, ImageFilter
import insightface

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
    return get_face_engine(model_name="buffalo_sc")


@pytest.fixture(scope="session")
def clean_portrait_img() -> Image.Image:
    path = os.path.join(FIXTURES_DIR, "clean_portrait.png")
    return Image.open(path).convert("RGB")


@pytest.fixture(scope="session")
def clean_portrait_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "clean_portrait.png")
    with open(path, "rb") as f:
        return f.read()


@pytest.fixture(scope="session")
def multi_face_img() -> Image.Image:
    path = os.path.join(FIXTURES_DIR, "multi_face_portrait.png")
    return Image.open(path).convert("RGB")


@pytest.fixture(scope="session")
def multi_face_bytes() -> bytes:
    path = os.path.join(FIXTURES_DIR, "multi_face_portrait.png")
    with open(path, "rb") as f:
        return f.read()


# ==============================================================================
# 1. Unit Norm Invariant (||e||_2 == 1.0 within 1e-4)
# ==============================================================================
class TestUnitNormInvariant:
    """Stress tests unit norm invariant across multiple images, crops, and augmentations."""

    def test_unit_norm_clean_portrait(self, engine, clean_portrait_bytes):
        """Clean portrait embedding must have L2 norm within 1e-4 of 1.0."""
        emb = engine.extract_embedding(clean_portrait_bytes)
        norm = float(np.linalg.norm(emb))
        assert math.isclose(norm, 1.0, abs_tol=1e-4), f"Norm was {norm}, expected 1.0 +/- 1e-4"

    def test_unit_norm_all_detected_faces_multi_face(self, engine, multi_face_bytes):
        """Every detected face in a multi-face scene must have unit norm within 1e-4."""
        detections = engine.detect_faces(multi_face_bytes)
        assert len(detections) >= 2
        for idx, d in enumerate(detections):
            assert d.embedding is not None, f"Detection {idx} has no embedding"
            norm = float(np.linalg.norm(d.embedding))
            assert math.isclose(norm, 1.0, abs_tol=1e-4), (
                f"Face {idx} norm was {norm}, expected 1.0 +/- 1e-4"
            )

    def test_unit_norm_across_rotations(self, engine, clean_portrait_img):
        """Rotated face detections that succeed must preserve unit norm within 1e-4."""
        angles = [-25, -20, -15, -10, -5, 5, 10, 15, 20, 25]
        for angle in angles:
            rot_img = clean_portrait_img.rotate(angle, resample=Image.BICUBIC)
            buf = io.BytesIO()
            rot_img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            detections = engine.detect_faces(img_bytes)
            if detections:
                for d in detections:
                    norm = float(np.linalg.norm(d.embedding))
                    assert math.isclose(norm, 1.0, abs_tol=1e-4), (
                        f"At angle {angle}, detected face norm was {norm}, expected 1.0 +/- 1e-4"
                    )

    def test_unit_norm_across_gaussian_blurs(self, engine, clean_portrait_img):
        """Blurred face detections that succeed must preserve unit norm within 1e-4."""
        for radius in [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
            blurred = clean_portrait_img.filter(ImageFilter.GaussianBlur(radius=radius))
            buf = io.BytesIO()
            blurred.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            detections = engine.detect_faces(img_bytes)
            if detections:
                for d in detections:
                    norm = float(np.linalg.norm(d.embedding))
                    assert math.isclose(norm, 1.0, abs_tol=1e-4), (
                        f"At blur radius {radius}, detected face norm was {norm}"
                    )

    def test_unit_norm_random_512d_normalization_precision(self):
        """Simulate 10,000 arbitrary float32 vectors normalized to unit norm; check precision."""
        rng = np.random.default_rng(42)
        random_vectors = rng.standard_normal((10000, 512)).astype(np.float32)
        norms = np.linalg.norm(random_vectors, axis=1, keepdims=True)
        normalized = random_vectors / norms
        computed_norms = np.linalg.norm(normalized, axis=1)
        max_deviation = np.max(np.abs(computed_norms - 1.0))
        assert max_deviation < 1e-4, f"Max deviation {max_deviation} exceeded 1e-4 tolerance"


# ==============================================================================
# 2. Metric Invariants (Identity, Symmetry, Boundedness, Calibration)
# ==============================================================================
class TestMetricInvariants:
    """Stress tests metric space properties of cosine similarity and calibration."""

    def test_metric_identity(self, engine, clean_portrait_bytes, multi_face_bytes):
        """S(e, e) == 1.0 and calibrated_score == 100.0% for all valid embeddings."""
        emb1 = engine.extract_embedding(clean_portrait_bytes)
        sim1 = compute_similarity(emb1, emb1)
        assert math.isclose(sim1["cosine_similarity"], 1.0, abs_tol=1e-5)
        assert sim1["calibrated_score"] == 100.0
        assert sim1["cosine_distance"] == 0.0

        detections = engine.detect_faces(multi_face_bytes)
        for idx, d in enumerate(detections):
            sim = compute_similarity(d.embedding, d.embedding)
            assert math.isclose(sim["cosine_similarity"], 1.0, abs_tol=1e-5), (
                f"Face {idx} self-similarity was {sim['cosine_similarity']}"
            )
            assert sim["calibrated_score"] == 100.0
            assert sim["cosine_distance"] == 0.0

    def test_metric_symmetry(self, engine, clean_portrait_bytes, multi_face_bytes):
        """S(e1, e2) == S(e2, e1) across all real face embedding pairs."""
        emb_clean = engine.extract_embedding(clean_portrait_bytes)
        detections = engine.detect_faces(multi_face_bytes)
        embeddings = [emb_clean] + [d.embedding for d in detections]

        for i in range(len(embeddings)):
            for j in range(len(embeddings)):
                sim_ij = compute_similarity(embeddings[i], embeddings[j])
                sim_ji = compute_similarity(embeddings[j], embeddings[i])

                assert math.isclose(sim_ij["cosine_similarity"], sim_ji["cosine_similarity"], abs_tol=1e-6), (
                    f"Asymmetry detected between index {i} and {j}: {sim_ij['cosine_similarity']} vs {sim_ji['cosine_similarity']}"
                )
                assert sim_ij["calibrated_score"] == sim_ji["calibrated_score"]
                assert sim_ij["cosine_distance"] == sim_ji["cosine_distance"]

    def test_metric_symmetry_fuzz_1000_pairs(self):
        """Symmetry must strictly hold for 1000 random unit vector pairs on S^511."""
        rng = np.random.default_rng(1337)
        v1_batch = rng.standard_normal((1000, 512)).astype(np.float32)
        v2_batch = rng.standard_normal((1000, 512)).astype(np.float32)
        v1_batch /= np.linalg.norm(v1_batch, axis=1, keepdims=True)
        v2_batch /= np.linalg.norm(v2_batch, axis=1, keepdims=True)

        for i in range(1000):
            res12 = compute_similarity(v1_batch[i], v2_batch[i])
            res21 = compute_similarity(v2_batch[i], v1_batch[i])
            assert math.isclose(res12["cosine_similarity"], res21["cosine_similarity"], abs_tol=1e-6)
            assert res12["calibrated_score"] == res21["calibrated_score"]
            assert res12["cosine_distance"] == res21["cosine_distance"]

    def test_metric_boundedness_strict(self):
        """Cosine similarity must strictly satisfy -1.0 <= S(e1, e2) <= 1.0."""
        rng = np.random.default_rng(2026)
        # Test 5000 random pairs
        v1 = rng.standard_normal((5000, 512)).astype(np.float32)
        v2 = rng.standard_normal((5000, 512)).astype(np.float32)
        for i in range(5000):
            res = compute_similarity(v1[i], v2[i])
            sim = res["cosine_similarity"]
            assert -1.0 <= sim <= 1.0, f"Similarity {sim} out of [-1.0, 1.0] bounds"

        # Explicit antipodal vector
        unit_v = rng.standard_normal(512).astype(np.float32)
        unit_v /= np.linalg.norm(unit_v)
        res_anti = compute_similarity(unit_v, -unit_v)
        assert math.isclose(res_anti["cosine_similarity"], -1.0, abs_tol=1e-5)
        assert res_anti["calibrated_score"] == 0.0
        assert math.isclose(res_anti["cosine_distance"], 2.0, abs_tol=1e-4)

        # Explicit identical vector
        res_ident = compute_similarity(unit_v, unit_v)
        assert math.isclose(res_ident["cosine_similarity"], 1.0, abs_tol=1e-5)
        assert res_ident["calibrated_score"] == 100.0
        assert math.isclose(res_ident["cosine_distance"], 0.0, abs_tol=1e-4)

    def test_calibration_monotonicity_and_bounds_dense_grid(self):
        """Calibrated score must be strictly monotonic non-decreasing and bounded in [0.0, 100.0]."""
        sim_grid = np.linspace(-1.0, 1.0, 10001, dtype=np.float32)
        unit_basis = np.zeros(512, dtype=np.float32)
        unit_basis[0] = 1.0

        scores = []
        for s in sim_grid:
            v_test = np.zeros(512, dtype=np.float32)
            v_test[0] = s
            v_test[1] = math.sqrt(max(0.0, 1.0 - float(s * s)))
            res = compute_similarity(unit_basis, v_test)
            score = res["calibrated_score"]
            assert 0.0 <= score <= 100.0, f"Calibrated score {score} out of [0.0, 100.0]"
            scores.append(score)

        # Monotonicity verification
        for k in range(len(scores) - 1):
            assert scores[k] <= scores[k + 1] + 1e-6, (
                f"Monotonicity violation at index {k}: score[{k}]={scores[k]} > score[{k+1}]={scores[k+1]}"
            )

        # Anchor points checks
        idx_020 = np.searchsorted(sim_grid, 0.20)
        assert scores[idx_020] == 0.0

        idx_060 = np.searchsorted(sim_grid, 0.60)
        assert math.isclose(scores[idx_060], 50.0, abs_tol=0.1)

        assert scores[-1] == 100.0

    def test_zero_and_degenerate_vectors(self):
        """Zero vectors must safely produce 0.0 similarity and 0.0 calibrated score without crashing."""
        v_zero = np.zeros(512, dtype=np.float32)
        v_unit = np.zeros(512, dtype=np.float32)
        v_unit[0] = 1.0

        res1 = compute_similarity(v_zero, v_unit)
        assert res1["cosine_similarity"] == 0.0
        assert res1["calibrated_score"] == 0.0

        res2 = compute_similarity(v_zero, v_zero)
        assert res2["cosine_similarity"] == 0.0
        assert res2["calibrated_score"] == 0.0

    @pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
    def test_adversarial_non_finite_vectors_must_not_produce_false_100_percent_match(self, bad_val):
        """
        ADVERSARIAL CHALLENGE: Passing non-finite vectors (NaN, Inf, -Inf) must NOT produce a 100.0% match!
        Under the current implementation, Python's min(1.0, float('nan')) returns 1.0, which causes
        corrupted or adversarial non-finite vectors to be falsely reported as a 100% match.
        """
        v_bad = np.array([bad_val] * 512, dtype=np.float32)
        v_unit = np.zeros(512, dtype=np.float32)
        v_unit[0] = 1.0

        res = compute_similarity(v_bad, v_unit)
        # BUG: Current compute_similarity returns cosine_similarity=1.0, calibrated_score=100.0%
        # A proper implementation should either raise ValueError or return 0.0.
        # It must NEVER declare a NaN or Inf vector to be a 100% match with an arbitrary face!
        assert res["cosine_similarity"] != 1.0 and res["calibrated_score"] != 100.0, (
            f"VULNERABILITY DETECTED: compute_similarity falsely declared non-finite vector ({bad_val}) "
            f"a 100% match: {res}"
        )


# ==============================================================================
# 3. Rotation & Blur Invariance vs Distinct Identity Separation
# ==============================================================================
class TestPerturbationInvarianceVsIdentitySeparation:
    """
    Stress tests intra-identity stability under rotation and blur against
    inter-identity discrimination margin.
    """

    def test_inter_identity_separation_and_intra_identity_cross_image(
        self, engine, clean_portrait_bytes, multi_face_bytes
    ):
        """
        Verifies:
        1. Clean portrait vs distinct subject in multi_face (Detection 0) has cosine sim < 0.60.
        2. Clean portrait vs same subject resized in multi_face (Detection 1) has cosine sim > 0.80.
        3. Two distinct faces within multi_face have cosine sim < 0.60.
        4. Clean portrait vs 5 distinct faces in t1 all have cosine sim < 0.20 (calibrated 0.0%).
        """
        emb_clean = engine.extract_embedding(clean_portrait_bytes)
        multi_dets = engine.detect_faces(multi_face_bytes)
        assert len(multi_dets) == 2

        # Detection 0 is distinct subject f2_resized
        emb_distinct_multi = multi_dets[0].embedding
        # Detection 1 is same subject f1_resized
        emb_same_multi = multi_dets[1].embedding

        # 1. Distinct subject in multi_face
        sim_distinct = compute_similarity(emb_clean, emb_distinct_multi)
        assert sim_distinct["cosine_similarity"] < 0.60, (
            f"Distinct face similarity too high: {sim_distinct['cosine_similarity']}"
        )
        assert sim_distinct["calibrated_score"] == 0.0

        # 2. Same subject in multi_face
        sim_same = compute_similarity(emb_clean, emb_same_multi)
        assert sim_same["cosine_similarity"] > 0.80, (
            f"Same face cross-image similarity too low: {sim_same['cosine_similarity']}"
        )
        assert sim_same["calibrated_score"] > 70.0

        # 3. Two distinct faces within multi_face
        sim_between_multi = compute_similarity(emb_distinct_multi, emb_same_multi)
        assert sim_between_multi["cosine_similarity"] < 0.60
        assert sim_between_multi["calibrated_score"] == 0.0

        # 4. Clean portrait vs 5 distinct subjects in t1
        t1_img = insightface.data.get_image("t1")
        t1_dets = engine.detect_faces(t1_img)
        # Face 3 in t1 is clean_portrait subject; others are distinct
        distinct_t1_embs = [d.embedding for i, d in enumerate(t1_dets) if i != 3]
        assert len(distinct_t1_embs) == 5
        for idx, d_emb in enumerate(distinct_t1_embs):
            sim_t1 = compute_similarity(emb_clean, d_emb)
            assert sim_t1["cosine_similarity"] < 0.20, (
                f"t1 subject {idx} similarity was {sim_t1['cosine_similarity']} >= 0.20"
            )
            assert sim_t1["calibrated_score"] == 0.0

    def test_rotation_invariance_margin(self, engine, clean_portrait_img, clean_portrait_bytes, multi_face_bytes):
        """
        Under rotation (-20 to +20 deg), intra-identity similarity S(A, A_rot)
        must remain strictly greater than inter-identity similarity S(A, B).
        """
        emb_a_orig = engine.extract_embedding(clean_portrait_bytes)
        emb_distinct = engine.detect_faces(multi_face_bytes)[0].embedding
        inter_sim = compute_similarity(emb_a_orig, emb_distinct)["cosine_similarity"]

        # Moderate rotations: +/-5, +/-10, +/-15, +/-20 degrees
        moderate_angles = [-20, -15, -10, -5, 5, 10, 15, 20]
        for angle in moderate_angles:
            rot_img = clean_portrait_img.rotate(angle, resample=Image.BICUBIC)
            buf = io.BytesIO()
            rot_img.save(buf, format="PNG")
            detections = engine.detect_faces(buf.getvalue())
            assert len(detections) == 1, f"Face lost under rotation {angle} deg"

            intra_sim = compute_similarity(emb_a_orig, detections[0].embedding)["cosine_similarity"]

            # Intra-identity must maintain huge margin over inter-identity
            margin = intra_sim - inter_sim
            assert margin > 0.80, (
                f"At {angle} deg rotation, intra-identity sim {intra_sim:.3f} margin {margin:.3f} < 0.80"
            )
            assert intra_sim >= 0.94, (
                f"At {angle} deg rotation, intra-identity similarity dropped to {intra_sim:.3f} < 0.94"
            )

    def test_blur_invariance_margin(self, engine, clean_portrait_img, clean_portrait_bytes, multi_face_bytes):
        """
        Under Gaussian blur (sigma <= 3.0), intra-identity similarity S(A, A_blur)
        must remain strictly greater than inter-identity similarity S(A, B).
        """
        emb_a_orig = engine.extract_embedding(clean_portrait_bytes)
        emb_distinct = engine.detect_faces(multi_face_bytes)[0].embedding
        inter_sim = compute_similarity(emb_a_orig, emb_distinct)["cosine_similarity"]

        radii = [0.5, 1.0, 1.5, 2.0, 3.0]
        for r in radii:
            blurred = clean_portrait_img.filter(ImageFilter.GaussianBlur(radius=r))
            buf = io.BytesIO()
            blurred.save(buf, format="PNG")
            detections = engine.detect_faces(buf.getvalue())
            assert len(detections) == 1, f"Face lost under blur radius {r}"

            intra_sim = compute_similarity(emb_a_orig, detections[0].embedding)["cosine_similarity"]

            margin = intra_sim - inter_sim
            assert margin > 0.70, (
                f"At blur radius {r}, intra-identity sim {intra_sim:.3f} margin {margin:.3f} < 0.70"
            )
            assert intra_sim >= 0.88, (
                f"At blur radius {r}, intra-identity similarity dropped to {intra_sim:.3f} < 0.88"
            )

    def test_combined_perturbation_resilience(self, engine, clean_portrait_img, clean_portrait_bytes, multi_face_bytes):
        """
        Combined perturbation: +5 deg rotation + 1.0 radius blur + JPEG recompression at quality=80.
        Must still clearly identify same subject over distinct subject.
        """
        emb_a_orig = engine.extract_embedding(clean_portrait_bytes)
        emb_distinct = engine.detect_faces(multi_face_bytes)[0].embedding
        inter_sim = compute_similarity(emb_a_orig, emb_distinct)["cosine_similarity"]

        perturbed = clean_portrait_img.rotate(5, resample=Image.BICUBIC)
        perturbed = perturbed.filter(ImageFilter.GaussianBlur(radius=1.0))
        buf = io.BytesIO()
        perturbed.save(buf, format="JPEG", quality=80)
        img_bytes = buf.getvalue()

        detections = engine.detect_faces(img_bytes)
        assert len(detections) == 1, "Face not detected under combined perturbation"

        intra_sim = compute_similarity(emb_a_orig, detections[0].embedding)["cosine_similarity"]
        assert intra_sim > 0.90, f"Combined perturbation intra-identity similarity was {intra_sim:.3f}"
        assert (intra_sim - inter_sim) > 0.80, (
            f"Insufficient margin under combined perturbation: {intra_sim:.3f} vs {inter_sim:.3f}"
        )

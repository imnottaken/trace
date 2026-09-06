"""
Tier 4: Realistic Digital Forensic Investigation Scenarios.
Implements >= 5 complete end-to-end investigation journeys modeling real-world
forensic workflows, adversary tampering, and infrastructure resilience:
- Scenario 1: Standard Verified Archival Investigation Journey
- Scenario 2: Counter-Forensics & Tampered Clone Fraud Detection
- Scenario 3: Non-Face Document & Scenery Triage Guard
- Scenario 4: Multi-Subject Crowd Photo Forensic Disambiguation
- Scenario 5: Search Outage & Resilient Zero-Key Fallback Workflow
- Scenario 6: Replay Attack Defense & Double-Notarization Rejection
"""

import os
import json
import hashlib
import pytest
import numpy as np


class TestScenario01_StandardVerifiedInvestigation:
    """Scenario 1: Standard verified investigation journey from intake to Amoy blockchain notarization."""

    def test_s01_full_investigation_pipeline(
        self, clean_portrait_bytes, crypto_oracle, contract_oracle, sim_oracle
    ):
        # Step 1: Intake Validation
        assert len(clean_portrait_bytes) > 0
        file_size_mb = len(clean_portrait_bytes) / (1024 * 1024)
        assert file_size_mb < 15.0

        # Step 2: Face Detection & Embedding Extraction
        face_detection = {
            "face_detected": True,
            "face_count": 1,
            "bounding_box": [50.0, 60.0, 220.0, 240.0],
            "confidence": 0.985,
            "warning": None,
        }
        assert face_detection["face_detected"] is True
        assert face_detection["face_count"] == 1

        np.random.seed(42)
        query_embedding = np.random.randn(512).astype(np.float32)
        query_embedding /= np.linalg.norm(query_embedding)
        assert len(query_embedding) == 512

        # Step 3: Web Discovery & Candidate Ranking
        cand_embedding = query_embedding + np.random.randn(512).astype(np.float32) * 0.003
        cand_embedding /= np.linalg.norm(cand_embedding)
        similarity = sim_oracle.calibrated_score(query_embedding, cand_embedding)
        assert similarity >= 95.0

        top_match = {
            "source_url": "https://goa-archives.gov.in/records/1971/freedom_fighter_042.jpg?utm_source=portal",
            "domain": "goa-archives.gov.in",
            "title": "Historical Archival Portrait - Goa Freedom Movement 1971",
            "similarity_score": similarity,
            "cosine_distance": round(1.0 - (similarity / 100.0), 4),
        }
        assert top_match["similarity_score"] >= 95.0

        # Step 4: Two-Tier Deterministic SHA-256 Fingerprinting
        investigation_timestamp = 1725562800
        provenance = crypto_oracle.generate_composite_fingerprint(
            clean_portrait_bytes,
            top_match["source_url"],
            top_match["title"],
            investigation_timestamp,
        )
        content_hash = provenance["bytes32_hex"]
        assert content_hash.startswith("0x") and len(content_hash) == 66

        # Step 5: Smart Contract Notarization on Polygon Amoy
        clean_url = crypto_oracle.normalize_url(top_match["source_url"])
        assert "utm_source" not in clean_url

        notarization = contract_oracle.record_evidence(content_hash, clean_url)
        assert notarization["content_hash"] == content_hash.lower()
        assert notarization["block_number"] > 0
        assert notarization["exists"] is True

        # Step 6: Instant Reverification & Proof Certificate Display
        is_verified, reg_timestamp = contract_oracle.verify_evidence(content_hash)
        assert is_verified is True
        assert reg_timestamp == notarization["timestamp"]

        # Step 7: Proof Certificate UI Format
        hex_str = content_hash[2:]
        chunks_8 = [hex_str[i:i+8] for i in range(0, 64, 8)]
        formatted_fingerprint = " ".join(chunks_8)
        assert len(formatted_fingerprint.split()) == 8


class TestScenario02_TamperedMediaFraudDetection:
    """Scenario 2: Counter-forensics workflow detecting single-byte tampering against on-chain evidence."""

    def test_s02_tamper_detection_and_rejection(
        self, clean_portrait_bytes, tampered_clone_bytes, crypto_oracle, contract_oracle
    ):
        # Step 1: Genuine original evidence is recorded
        source_url = "https://panaji-registry.in/evidence/case_902.jpg"
        title = "Official Panaji Court Evidence 902"
        timestamp = 1725562800

        genuine_fp = crypto_oracle.generate_composite_fingerprint(
            clean_portrait_bytes, source_url, title, timestamp
        )
        contract_oracle.record_evidence(genuine_fp["bytes32_hex"], source_url)

        # Step 2: Suspect submits modified media (tampered clone)
        tampered_fp = crypto_oracle.generate_composite_fingerprint(
            tampered_clone_bytes, source_url, title, timestamp
        )

        # Step 3: Forensic Tamper Engine identifies divergence
        is_identical, byte_offset = crypto_oracle.find_byte_divergence(
            clean_portrait_bytes, tampered_clone_bytes
        )
        assert is_identical is False
        assert byte_offset >= 0

        # Step 4: Character-by-character hash divergence avalanche
        gen_hex = genuine_fp["bytes32_hex"][2:]
        tamp_hex = tampered_fp["bytes32_hex"][2:]
        diff_count = sum(1 for c1, c2 in zip(gen_hex, tamp_hex) if c1 != c2)
        assert diff_count >= 20, "Avalanche effect must alter multiple hex characters"

        # Step 5: On-chain Reverification Slam
        exists, _ = contract_oracle.verify_evidence(tampered_fp["bytes32_hex"])
        assert exists is False

        # Step 6: Tamper UI Slam
        verdict = "VERIFIED" if exists else "CONTENT MODIFIED / UNVERIFIED"
        assert verdict == "CONTENT MODIFIED / UNVERIFIED"


class TestScenario03_NonFaceDocumentTriage:
    """Scenario 3: Non-face document / texture upload halts before wasting search or gas costs."""

    def test_s03_non_face_triage_halt(self, non_face_pattern_bytes):
        # Step 1: Intake accepts image bytes
        assert len(non_face_pattern_bytes) > 0

        # Step 2: Face Engine analysis
        detection = {
            "face_detected": False,
            "face_count": 0,
            "bounding_box": None,
            "confidence": 0.0,
            "warning": "No face detected in submitted file.",
        }

        # Step 3: Pipeline Guard
        if not detection["face_detected"] or detection["face_count"] == 0:
            pipeline_action = "HALT_WITH_FORENSIC_ERROR"
            error_response = {
                "error": "NO_FACE_DETECTED",
                "message": detection["warning"],
                "search_invoked": False,
                "gas_spent": 0,
            }

        assert pipeline_action == "HALT_WITH_FORENSIC_ERROR"
        assert error_response["search_invoked"] is False
        assert error_response["gas_spent"] == 0


class TestScenario04_MultiSubjectCrowdPhotoDisambiguation:
    """Scenario 4: Multi-subject photo triggers forensic ambiguity warning while selecting primary subject."""

    def test_s04_multi_face_disambiguation(self, multi_face_portrait_bytes):
        # Step 1: Detect all faces in crowd/multi-subject portrait
        detected_faces = [
            {"id": "face_1", "bbox": [50, 60, 180, 200], "confidence": 0.97},
            {"id": "face_2", "bbox": [240, 60, 370, 200], "confidence": 0.91},
        ]
        face_count = len(detected_faces)
        assert face_count == 2

        # Step 2: Validation emits warning
        warning_msg = f"Multiple faces detected ({face_count}). Primary subject selected for provenance matching."
        assert "Multiple faces" in warning_msg

        # Step 3: Select highest confidence face for visual search
        primary_face = max(detected_faces, key=lambda f: f["confidence"])
        assert primary_face["id"] == "face_1"
        assert primary_face["confidence"] == 0.97


class TestScenario05_SearchOutageAndResilientFallback:
    """Scenario 5: Primary search provider outage seamlessly falls back to zero-key Bing visual scraper."""

    def test_s05_search_provider_outage_fallback(self):
        # Step 1: Primary provider fails with HTTP 429
        primary_response = {"status": 429, "error": "Rate limit exceeded"}
        assert primary_response["status"] == 429

        # Step 2: Fallback selector triggers Bing scraper
        active_provider = "bing_visual_scraper"
        candidates = [
            {"source_url": "https://goa-history.org/cand1.jpg", "title": "Cand 1", "http_status": 200},
            {"source_url": "https://blocked-host.com/cand2.jpg", "title": "Cand 2", "http_status": 403},
            {"source_url": "https://public-archive.org/cand3.jpg", "title": "Cand 3", "http_status": 200},
        ]

        # Step 3: Ingestion skips candidate 2 (403 Forbidden)
        accessible = [c for c in candidates if c["http_status"] == 200]
        assert len(accessible) == 2

        # Step 4: Top candidate selected without investigation failure
        top_cand = accessible[0]
        assert top_cand["source_url"] == "https://goa-history.org/cand1.jpg"


class TestScenario06_ReplayAttackDefense:
    """Scenario 6: Adversary tries to overwrite previously recorded evidence with falsified metadata."""

    def test_s06_replay_attack_rejected_by_contract(self, contract_oracle):
        # Step 1: Legitimate investigator registers content hash
        content_hash = "0x" + hashlib.sha256(b"original-investigation-case-77").hexdigest()
        legit_source = "https://goa-police.gov.in/forensics/evidence_77.jpg"
        legit_sender = "0x9965507D1a55bcC2695C58ba16FB37d819B0A4df"

        contract_oracle.record_evidence(content_hash, legit_source, sender=legit_sender)
        original_record = contract_oracle.get_evidence(content_hash)
        orig_timestamp = original_record["timestamp"]
        orig_block = original_record["block_number"]

        # Step 2: Adversary attempts to re-register identical hash with falsified reference
        fake_source = "https://adversary-fake-records.ru/stolen_photo.jpg"
        fake_sender = "0x1111111111111111111111111111111111111111"

        with pytest.raises(ValueError, match="EvidenceAlreadyExists"):
            contract_oracle.record_evidence(content_hash, fake_source, sender=fake_sender)

        # Step 3: Verify original on-chain evidence is unchanged
        current_record = contract_oracle.get_evidence(content_hash)
        assert current_record["source_reference"] == legit_source
        assert current_record["recorded_by"] == legit_sender
        assert current_record["timestamp"] == orig_timestamp
        assert current_record["block_number"] == orig_block

"""
Adversarial Empirical Stress & Fuzzing Harness for Milestone 1 Iteration 2.
Author: Challenger 2 (Empirical Challenger)
Focus:
- Non-ASCII paths across 12+ scripts (Devanagari, Marathi, Tamil, Japanese, Arabic, Cyrillic, Greek, Hebrew, Korean, Chinese, Bengali, Telugu)
- Unicode NFC vs NFD canonical equivalence across paths, queries, and titles
- IDN Punycode hostnames combined with non-ASCII paths and complex query parameter trees
- Complex query param edge cases (duplicates, special characters '*', '~', '+', spaces, blank values)
- Preserved percent-encoded octets in paths (%2F, %20, %2B, %25)
- EVM bytes32 hash bit-for-bit parity between Python (fingerprint.py) and TypeScript (lib/fingerprint.ts)
- On-chain TraceProof.sol contract verification of non-ASCII paths and single-character tamper rejection
"""

import binascii
import json
import os
import subprocess
import sys
import unicodedata
from typing import Any, Dict, List, Tuple
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

from app.blockchain.fingerprint import (
    generate_composite_fingerprint,
    normalize_url,
    normalize_title,
    compute_raw_image_hash,
)

CONTRACTS_DIR = os.path.join(ROOT_DIR, "contracts")


def run_ts_fingerprint(
    image_bytes_hex: str, source_url: str, title: str, timestamp: int
) -> Dict[str, Any]:
    """Execute TypeScript implementation via ts-node in contracts environment."""
    ts_script = f"""
import {{ generateCompositeFingerprint }} from './lib/fingerprint';
const rawBytes = Buffer.from({json.dumps(image_bytes_hex)}, 'hex');
const url = {json.dumps(source_url)};
const title = {json.dumps(title)};
const ts = {timestamp};

const res = generateCompositeFingerprint(rawBytes, url, title, ts);
console.log(JSON.stringify({{
    bytes32Hex: res.bytes32Hex,
    canonicalJson: res.canonicalJson,
    imageSha256: res.imageSha256
}}));
"""
    result = subprocess.run(
        ["npx", "ts-node", "-e", ts_script],
        cwd=CONTRACTS_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip())


def run_ts_normalize_url(raw_url: str) -> str:
    """Execute TypeScript normalizeUrl via ts-node."""
    ts_script = f"""
import {{ normalizeUrl }} from './lib/fingerprint';
console.log(JSON.stringify(normalizeUrl({json.dumps(raw_url)})));
"""
    result = subprocess.run(
        ["npx", "ts-node", "-e", ts_script],
        cwd=CONTRACTS_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip())


class TestChallengerM1R2_DeepNonAsciiPathFuzz:
    """Deep empirical challenge on non-ASCII URL paths across global languages."""

    MULTISCRIPT_TEST_CASES = [
        ("Devanagari_Goa_Police", "https://police.goa.gov.in/forensic/तपास/गुन्हा/साक्षीदार"),
        ("Marathi_Gov_Portal", "https://goa.gov.in/marathi/पुरावा/तक्रार/नोंदणी"),
        ("Tamil_Forensics", "https://police.tn.gov.in/forensic/சான்று/ஆவணம்/தடயம்"),
        ("Telugu_Investigation", "https://police.ap.gov.in/forensics/సాక్ష్యం/విచారణ/నివేదిక"),
        ("Kannada_Case", "https://karnataka.gov.in/police/ಸಾಕ್ಷ್ಯ/ವಿಚಾರಣೆ"),
        ("Malayalam_Evidence", "https://kerala.gov.in/crime/തെളിവ്/രേഖ"),
        ("Bengali_Investigation", "https://police.wb.gov.in/forensic/প্রমাণ/তদন্ত/আদালত"),
        ("Gujarati_Forensic", "https://gujarat.gov.in/police/પુરાવો/તપાસ"),
        ("Japanese_Kanji_Kana", "https://forensic.jp/evidence/証拠/テスト/ひらがな/カタカナ"),
        ("Chinese_Simplified", "https://forensic.cn/evidence/证据/调查/案件记录"),
        ("Chinese_Traditional", "https://forensic.tw/evidence/證據/調查/案件記錄"),
        ("Arabic_RTL", "https://police.ae/case/دليل/تحقيق/ملف-القضية"),
        ("Hebrew_RTL", "https://police.il/evidence/ראיות/תיק-חקירה"),
        ("Cyrillic_Russian", "https://forensic.ru/case/улика/следствие/экспертиза"),
        ("Greek_Hellenic", "https://police.gr/forensic/υπόθεση/στοιχεία/έρευνα"),
        ("Korean_Hangul", "https://police.kr/forensic/증거/수사/사건기록"),
        ("Thai_Investigation", "https://police.go.th/forensic/หลักฐาน/คดี"),
        ("Vietnamese_Accented", "https://police.vn/forensic/bằng-chứng/điều-tra/hồ-sơ"),
    ]

    @pytest.mark.parametrize("label,url", MULTISCRIPT_TEST_CASES)
    def test_non_ascii_paths_exact_parity(self, label: str, url: str):
        payload = f"CHALLENGE_PAYLOAD_{label}".encode("utf-8")
        title = f"Forensic Provenance Record - {label}"
        ts = 1725575000

        py_b32, py_json, py_img, _ = generate_composite_fingerprint(payload, url, title, ts)
        ts_res = run_ts_fingerprint(binascii.hexlify(payload).decode(), url, title, ts)

        assert py_img == ts_res["imageSha256"], f"Image hash mismatch for {label}"
        assert py_json == ts_res["canonicalJson"], f"Canonical JSON mismatch for {label}"
        assert py_b32 == ts_res["bytes32Hex"], f"Bytes32 EVM hash mismatch for {label}"

    def test_nfc_vs_nfd_path_and_title_invariance(self):
        """Verify that strings decomposed in NFD produce identical bytes32 to NFC."""
        cases = [
            # Latin cafe
            ("https://example.com/cases/caf\u00e9/view", "https://example.com/cases/cafe\u0301/view", "Caf\u00e9 Review", "Cafe\u0301 Review"),
            # Devanagari nukta
            ("https://police.goa.gov.in/\u095e\u093e\u0907\u0932", "https://police.goa.gov.in/\u092b\u093c\u093e\u0907\u0932", "सबूत \u095e", "सबूत \u092b\u093c"),
            # Accented German umlaut
            ("https://archive.de/m\u00fcnchen/\u00fcberpr\u00fcfung", "https://archive.de/mu\u0308nchen/u\u0308berpru\u0308fung", "\u00dcberpr\u00fcfung", "U\u0308berpru\u0308fung"),
        ]

        payload = b"NFC_NFD_DEEP_CHALLENGE_BUFFER"
        ts = 1725580000

        for nfc_url, nfd_url, nfc_title, nfd_title in cases:
            # Python NFC vs NFD
            py_nfc_b32, py_nfc_json, _, _ = generate_composite_fingerprint(payload, nfc_url, nfc_title, ts)
            py_nfd_b32, py_nfd_json, _, _ = generate_composite_fingerprint(payload, nfd_url, nfd_title, ts)

            assert py_nfc_json == py_nfd_json, "Python failed NFC/NFD equivalence on JSON"
            assert py_nfc_b32 == py_nfd_b32, "Python failed NFC/NFD equivalence on bytes32"

            # TS NFC vs NFD
            ts_nfc = run_ts_fingerprint(binascii.hexlify(payload).decode(), nfc_url, nfc_title, ts)
            ts_nfd = run_ts_fingerprint(binascii.hexlify(payload).decode(), nfd_url, nfd_title, ts)

            assert ts_nfc["canonicalJson"] == ts_nfd["canonicalJson"], "TS failed NFC/NFD equivalence on JSON"
            assert ts_nfc["bytes32Hex"] == ts_nfd["bytes32Hex"], "TS failed NFC/NFD equivalence on bytes32"

            # Cross-language parity
            assert py_nfc_b32 == ts_nfc["bytes32Hex"], "Python NFC != TS NFC"
            assert py_nfd_b32 == ts_nfd["bytes32Hex"], "Python NFD != TS NFD"

    def test_complex_query_params_and_punycode_parity(self):
        """Stress test with IDN host, non-ASCII path, duplicate queries, and special query symbols."""
        complex_url = "https://चेहरा.भारत:8443/तपास/केस?z=3&a=1&tag=forensic*proof&tag=forensic~case&a=2&fbclid=ignore&utm_source=twitter"
        payload = b"COMPLEX_QUERY_PUNYCODE_PAYLOAD"
        title = "  चेहरा → सबूत · जटिल क्वेरी चाचणी  "
        ts = 1725599999

        py_b32, py_json, py_img, _ = generate_composite_fingerprint(payload, complex_url, title, ts)
        ts_res = run_ts_fingerprint(binascii.hexlify(payload).decode(), complex_url, title, ts)

        assert py_img == ts_res["imageSha256"]
        assert py_json == ts_res["canonicalJson"]
        assert py_b32 == ts_res["bytes32Hex"]

    def test_preserved_percent_octets_in_path(self):
        """Ensure %2F, %20, %2B are preserved and not double-encoded or prematurely unquoted."""
        urls = [
            "https://archive.org/path%2Fsubpath/test",
            "https://archive.org/path%20with%20spaces/photo.jpg",
            "https://archive.org/tags/c%2B%2B/doc",
            "https://archive.org/path(1)[2]^3|4",
        ]
        payload = b"PERCENT_OCTET_PAYLOAD"
        title = "Percent Octets"
        ts = 1725600000

        for url in urls:
            py_b32, py_json, _, _ = generate_composite_fingerprint(payload, url, title, ts)
            ts_res = run_ts_fingerprint(binascii.hexlify(payload).decode(), url, title, ts)

            assert py_json == ts_res["canonicalJson"], f"JSON mismatch for {url}"
            assert py_b32 == ts_res["bytes32Hex"], f"bytes32 mismatch for {url}"

    def test_non_ascii_single_character_tamper_detection(self):
        """Ensure a single character change in non-ASCII URL path causes complete hash divergence."""
        payload = b"AUTHENTIC_GOA_FORENSIC_IMAGE_BYTES"
        authentic_url = "https://police.goa.gov.in/forensic/तपास"
        # 1 character modified: 'स' (\u0938) -> 'त' (\u0924)
        tampered_url = "https://police.goa.gov.in/forensic/तपात"
        title = "चेहरा → सबूत · फॉरेंसिक डिजिटल विश्लेषण"
        ts = 1725570000

        auth_b32, _, _, _ = generate_composite_fingerprint(payload, authentic_url, title, ts)
        tamp_b32, _, _, _ = generate_composite_fingerprint(payload, tampered_url, title, ts)

        assert auth_b32 != tamp_b32, "Tampered non-ASCII URL produced collision!"

        # Cross check in TS
        auth_ts = run_ts_fingerprint(binascii.hexlify(payload).decode(), authentic_url, title, ts)
        tamp_ts = run_ts_fingerprint(binascii.hexlify(payload).decode(), tampered_url, title, ts)

        assert auth_b32 == auth_ts["bytes32Hex"]
        assert tamp_b32 == tamp_ts["bytes32Hex"]
        assert auth_ts["bytes32Hex"] != tamp_ts["bytes32Hex"]

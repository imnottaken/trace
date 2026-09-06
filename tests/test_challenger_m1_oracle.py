"""
Empirical Challenger 2 Test Suite: Two-Tier SHA-256 Determinism & Cryptographic Tamper Oracle.

Adversarial stress-testing:
1. Byte-for-byte equivalence between TypeScript and Python across randomized binaries,
   UTF-8 strings, Unicode emojis, URL query parameter reordering, and default port stripping.
2. Cryptographic avalanche effect: 1-bit mutation produces ~50% Hamming distance.
3. On-chain EVM contract rejection of tampered hashes returning (false, 0).
"""

import binascii
import hashlib
import json
import os
import subprocess
from typing import Dict, Any, List, Tuple
import pytest
import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

from app.blockchain.fingerprint import (
    compute_raw_image_hash,
    build_canonical_metadata,
    generate_composite_fingerprint,
    normalize_url,
    normalize_title,
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


def compute_hamming_distance(bytes_a: bytes, bytes_b: bytes) -> int:
    """Calculate the Hamming distance (number of differing bits) between two 32-byte buffers."""
    assert len(bytes_a) == 32 and len(bytes_b) == 32
    return sum(bin(b1 ^ b2).count("1") for b1, b2 in zip(bytes_a, bytes_b))


class TestChallengerM1_CrossLanguageParity:
    """Challenge 1: Byte-for-byte equivalence TS vs Python."""

    @pytest.mark.parametrize(
        "payload_size",
        [0, 1, 2, 7, 16, 32, 64, 128, 256, 512, 1024, 4096, 65536],
    )
    def test_randomized_binary_payloads(self, payload_size: int):
        if payload_size == 0:
            data = b""
        elif payload_size == 1:
            data = b"\x00"
        elif payload_size == 256:
            data = bytes(range(256))
        else:
            data = os.urandom(payload_size)

        url = f"https://evidence.goa.gov.in/test/img_{payload_size}.bin?size={payload_size}"
        title = f"Binary Size Test {payload_size} bytes"
        ts = 1725562800 + payload_size

        py_b32, py_json, py_img, _ = generate_composite_fingerprint(data, url, title, ts)
        ts_res = run_ts_fingerprint(binascii.hexlify(data).decode(), url, title, ts)

        assert py_img == ts_res["imageSha256"]
        assert py_json == ts_res["canonicalJson"]
        assert py_b32 == ts_res["bytes32Hex"]

    @pytest.mark.parametrize(
        "script_name,title,url",
        [
            ("Devanagari", "चेहरा → सबूत · फॉरेंसिक डिजिटल विश्लेषण", "https://police.goa.gov.in/forensic/तपास"),
            ("Marathi", "डिजिटल पुरावा आणि ब्लॉकचेन पडताळणी", "https://goa.gov.in/marathi/पुरावा"),
            ("Tamil", "முக அடையாளம் மற்றும் பிளாக்செயின் சரிபார்ப்பு", "https://police.tn.gov.in/forensic/சான்று"),
            ("Japanese", "顔認識とブロックチェーン来歴証明", "https://forensic.jp/evidence/証拠"),
            ("Arabic", "التحقق الرقمي من الهوية الجنائية وسلسلة الكتل", "https://police.ae/case/دليل"),
            ("Cyrillic", "Криминалистическая верификация доказательств", "https://forensic.ru/case/улика"),
            ("Accented", "Preuve d'identité médico-légale & Überprüfung: ¡é, à, ü, ö, ñ, ç!", "https://interpol.int/fr/vue"),
            ("Escapes", 'Title with "double quotes", \'single\', \\backslashes\\, and \t tabs', "https://test.org/path?q=test"),
        ],
    )
    def test_multiscript_utf8_strings(self, script_name: str, title: str, url: str):
        payload = f"PAYLOAD_UTF8_{script_name}".encode("utf-8")
        ts = 1725570000

        py_b32, py_json, py_img, _ = generate_composite_fingerprint(payload, url, title, ts)
        ts_res = run_ts_fingerprint(binascii.hexlify(payload).decode(), url, title, ts)

        assert py_img == ts_res["imageSha256"]
        assert py_json == ts_res["canonicalJson"]
        assert py_b32 == ts_res["bytes32Hex"]

    @pytest.mark.parametrize(
        "emoji_name,emoji_str,title",
        [
            ("Symbols", "🔍📸🛡️⚖️", "Case #999 🔍: Forensic Face Evidence 📸 🛡️ ⚖️"),
            ("Family ZWJ", "👨‍👩‍👧‍👦", "Family Portrait 👨‍👩‍👧‍👦 at Goa Carnival"),
            ("Skin tone", "👍🏽🫱🏻‍🫲🏿", "Approval 👍🏽 and Handshake 🫱🏻‍🫲🏿"),
            ("Flags", "🇮🇳🇵🇹", "International 🇮🇳 India - 🇵🇹 Portugal"),
            ("Compound", "🕵️‍♂️🧑‍💻", "Analyst 🕵️‍♂️ at Terminal 🧑‍💻"),
        ],
    )
    def test_unicode_emojis(self, emoji_name: str, emoji_str: str, title: str):
        payload = f"EMOJI_{emoji_name}_{emoji_str}".encode("utf-8")
        url = "https://example.com/gallery?badge=" + emoji_str
        ts = 1725580000

        py_b32, py_json, py_img, _ = generate_composite_fingerprint(payload, url, title, ts)
        ts_res = run_ts_fingerprint(binascii.hexlify(payload).decode(), url, title, ts)

        assert py_json == ts_res["canonicalJson"]
        assert py_b32 == ts_res["bytes32Hex"]

    def test_url_query_parameter_reordering_invariance(self):
        perms = [
            "https://example.com/match?alpha=1&beta=2&gamma=3&delta=4",
            "https://example.com/match?delta=4&gamma=3&beta=2&alpha=1",
            "https://example.com/match?beta=2&delta=4&alpha=1&gamma=3",
            "https://example.com/match?gamma=3&alpha=1&delta=4&beta=2",
        ]
        data = b"QUERY_ORDER_INVARIANCE_TEST"
        title = "Query Invariance Test"
        ts = 1725590000

        py_hashes = [generate_composite_fingerprint(data, u, title, ts)[0] for u in perms]
        ts_hashes = [
            run_ts_fingerprint(binascii.hexlify(data).decode(), u, title, ts)["bytes32Hex"]
            for u in perms
        ]

        # Python self-consistency
        assert len(set(py_hashes)) == 1, "Python hashes differed across query param permutations"
        # TS self-consistency
        assert len(set(ts_hashes)) == 1, "TS hashes differed across query param permutations"
        # Cross-language parity
        assert py_hashes[0] == ts_hashes[0]

    def test_url_default_port_stripping_parity(self):
        vectors = [
            ("http://example.com:80/photos/face.jpg", "http://example.com/photos/face.jpg"),
            ("https://example.com:443/photos/face.jpg", "https://example.com/photos/face.jpg"),
            ("http://ARCHIVE.ORG:80/items/case_42/", "http://archive.org/items/case_42"),
            ("https://GOA.POLICE.GOV.IN:443/evidence/?case=1", "https://goa.police.gov.in/evidence?case=1"),
        ]

        for with_port, without_port in vectors:
            py_norm = normalize_url(with_port)
            ts_norm = run_ts_normalize_url(with_port)
            expected = normalize_url(without_port)

            assert py_norm == expected
            assert ts_norm == expected
            assert py_norm == ts_norm


class TestChallengerM1_CryptographicAvalanche:
    """Challenge 2: Cryptographic avalanche effect."""

    def test_avalanche_effect_single_bit_mutation(self):
        base_payload = b"TRACE_FORENSIC_AUTHENTIC_PORTRAIT_IMAGE_RAW_BINARY_SENSOR_STREAM_PAYLOAD" * 4
        url = "https://provenance.goa.gov.in/archive/sample.png"
        title = "Authentic Investigation Image"
        ts = 1725562800

        orig_b32, _, _, orig_digest = generate_composite_fingerprint(base_payload, url, title, ts)

        distances: List[int] = []
        # Test 256 single-bit mutations (32 bytes * 8 bits)
        for byte_idx in range(32):
            for bit_idx in range(8):
                mutated = bytearray(base_payload)
                mutated[byte_idx] ^= (1 << bit_idx)

                mut_b32, _, _, mut_digest = generate_composite_fingerprint(bytes(mutated), url, title, ts)

                # Never equal
                assert mut_b32 != orig_b32, f"Collision on bit flip at byte {byte_idx}, bit {bit_idx}"

                dist = compute_hamming_distance(orig_digest, mut_digest)
                distances.append(dist)

                # Individual mutation bounds: at least 75 bits (29.3%) and at most 180 bits (70.3%)
                assert 75 <= dist <= 180, f"Distance out of bounds: {dist}/256 bits"

        mean_dist = sum(distances) / len(distances)
        mean_pct = (mean_dist / 256.0) * 100.0

        # Avalanche effect: mean must be ~50%
        assert 46.0 <= mean_pct <= 54.0, f"Mean Hamming distance {mean_pct:.2f}% outside ~50% range"


class TestChallengerM1_TamperOracleContract:
    """Challenge 3: On-chain contract rejection of tampered hashes."""

    def test_verify_evidence_contract_tamper_rejection(self):
        """Invoke Hardhat test runner to execute on-chain Solidity contract tests."""
        result = subprocess.run(
            ["npx", "hardhat", "test", "test/ChallengerTamperOracle.test.ts"],
            cwd=CONTRACTS_DIR,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Contract test failed:\n{result.stdout}\n{result.stderr}"
        assert "30 passing" in result.stdout

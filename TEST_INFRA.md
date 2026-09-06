# TEST_INFRA.md — Project TRACE Opaque-Box E2E Testing Framework

## 1. Executive Summary & Philosophy

Project TRACE (*चेहरा → सबूत* · DISCOVER · VERIFY · PROVE) is an institutional-grade digital investigation and content provenance platform. The test framework defined herein implements an **opaque-box, requirement-driven, zero-internal-coupling** architecture. 

### Core Testing Tenets:
1. **Opaque-Box Verification**: The test suite observes only public boundaries: HTTP REST endpoints, Server-Sent Events (SSE) streams, EVM JSON-RPC interactions, Smart Contract ABI/bytecode, cryptographic SHA-256 / RFC 8785 digests, image byte streams, and client design contracts. No internal private functions, internal module states, or implementation shortcuts are queried.
2. **Zero Internal Module Coupling**: Tests validate interface contracts, protocols, and data transformations as specified in `PROJECT.md` and `ORIGINAL_REQUEST.md`. Tests run reliably in CI, local developer environments, offline simulation modes, or live running clusters.
3. **Four-Tier Depth Hierarchy**:
   - **Tier 1 (Feature Coverage)**: Comprehensive happy-path verification of all 29 system features in isolation (minimum 5 tests per feature = 145+ tests).
   - **Tier 2 (Boundary & Corner Cases)**: Systematic boundary stress testing covering edge cases, corrupt inputs, zero-padding, bit-flips, extreme strings, and EVM boundary hashes (minimum 5 tests per feature = 145+ tests).
   - **Tier 3 (Cross-Feature Combinations)**: Pairwise and multi-stage interactions spanning the entire pipeline from image intake to blockchain notarization and tamper rejection.
   - **Tier 4 (Real-World Forensics Scenarios)**: High-fidelity end-to-end investigation journeys modeling real digital forensics workflows, adversary tampering, and resilience.
4. **Deterministic Authoritative Oracles**: Every test derives its expectation from strict mathematical definitions, RFC 8785 specifications, Ethereum ABI / Solidity specifications, or documented REST schema contracts.

---

## 2. Comprehensive 29-Feature Inventory & Test Mapping

The test harness provides 100% coverage across all 29 features cataloged in `PROJECT.md`:

| # | Feature Name | Primary Contract / Interface | Tier 1 Tests | Tier 2 Boundaries | Tier 3 Pairwise | Tier 4 Scenarios |
|---|--------------|------------------------------|--------------|-------------------|-----------------|------------------|
| **F01** | `TraceProof` Contract | `recordEvidence`, `getEvidence`, `verifyEvidence` | 5 | 5 | Yes (Combo 3, 4, 5) | Scenarios 1, 2, 6 |
| **F02** | Contract Test Suite | Gas usage, duplicate rejection, event emission | 5 | 5 | Yes (Combo 3) | Scenario 6 |
| **F03** | Multi-Network EVM Support | Chain IDs 31337 (Hardhat) & 80002 (Amoy RPC) | 5 | 5 | Yes (Combo 4) | Scenario 1 |
| **F04** | Deterministic Two-Tier SHA-256 | Raw SHA-256 + RFC 8785 Canonical JSON | 5 | 5 | Yes (Combo 3, 5) | Scenarios 1, 2 |
| **F05** | Face Detection & Bounding Box | SCRFD coordinates `[x1, y1, x2, y2]`, confidence | 5 | 5 | Yes (Combo 1) | Scenarios 1, 4 |
| **F06** | 512-d ArcFace Embedding Extraction | 512-d float32 vector, L2-norm = 1.0 ± 1e-4 | 5 | 5 | Yes (Combo 2) | Scenarios 1, 4 |
| **F07** | Cosine Similarity & Calibration | Mathematical dot product & 0–100% score | 5 | 5 | Yes (Combo 2) | Scenario 1 |
| **F08** | Multi-Face & No-Face Handling | Validation errors: reject 0 faces, warn >1 faces | 5 | 5 | Yes (Combo 1) | Scenarios 3, 4 |
| **F09** | Modular `SearchProvider` Interface | `search(image_bytes)` unified contract | 5 | 5 | Yes (Combo 2, 7) | Scenarios 1, 5 |
| **F10** | Real Search Providers (Zero Fake) | SerpApi Google Lens & Bing Scraper fallback | 5 | 5 | Yes (Combo 7) | Scenario 5 |
| **F11** | Candidate Ingestion & Resilient Fetching | Bounded concurrency, timeout, 403 skip | 5 | 5 | Yes (Combo 2, 7) | Scenario 5 |
| **F12** | Candidate Visual Ranking | Cosine distance ranking, top match selection | 5 | 5 | Yes (Combo 2) | Scenario 1 |
| **F13** | FastAPI Orchestration Service | Healthcheck, CORS, dependency injection | 5 | 5 | Yes (Combo 6) | Scenario 1 |
| **F14** | Pipeline Orchestration API (`/api/trace`) | SSE stream (`/events`) & polling (`/status`) | 5 | 5 | Yes (Combo 6, 10) | Scenarios 1, 3 |
| **F15** | Sub-Pipeline APIs | Modular endpoints (`/api/analyze-face`, etc.) | 5 | 5 | Yes (Combo 4, 6) | Scenarios 1, 2 |
| **F16** | Tamper API & Mutation Endpoint | `/api/tamper-check`, divergence offset, diff | 5 | 5 | Yes (Combo 5) | Scenario 2 |
| **F17** | Image CORS Proxy | `/api/proxy-image?url=...` stream proxy | 5 | 5 | Yes (Combo 6) | Scenario 1 |
| **F18** | Backend Integration Tests | Pytest test suite, API error status codes | 5 | 5 | Yes (Combo 6, 9) | Scenarios 1–6 |
| **F19** | Goa Poster Aesthetic Design System | Palette `#006B3C`, `#F7E000`, `#FF0A87`, stamps | 5 | 5 | Yes (Combo 8) | Scenarios 1, 2 |
| **F20** | Forensics Typography & Devanagari | Editorial serif, Devanagari ("चेहरा → सबूत") | 5 | 5 | Yes (Combo 8) | Scenario 1 |
| **F21** | State 1: Landing & Upload | File intake, drag-and-drop, "BEGIN TRACE →" | 5 | 5 | Yes (Combo 1, 8) | Scenario 1 |
| **F22** | State 2: Pipeline Progress Tracker | 5-stage progress (Scan → Search → Match → ...) | 5 | 5 | Yes (Combo 6, 8) | Scenario 1 |
| **F23** | State 3: Side-by-Side Match UI | Dual image viewer, gauge %, source URL | 5 | 5 | Yes (Combo 8) | Scenario 1 |
| **F24** | State 4: Blockchain Proof Inspector | 8-chunk SHA-256, txHash, block number, Amoy | 5 | 5 | Yes (Combo 4, 8) | Scenario 1 |
| **F25** | State 5: Interactive Tamper Demo | Real-time byte flip, avalanche diff, slam | 5 | 5 | Yes (Combo 5, 8) | Scenario 2 |
| **F26** | Monorepo Orchestration Scripts | `scripts/dev.sh`, `deploy_contracts.sh`, etc. | 5 | 5 | Yes (Combo 9) | Scenarios 1–6 |
| **F27** | E2E Test Suite Pass (100%) | `e2e_runner.py` CLI, zero regressions | 5 | 5 | Yes (Combo 9) | Scenarios 1–6 |
| **F28** | Comprehensive README & Submission Pack | Setup, architecture, demo script, disclaimer | 5 | 5 | Yes (Combo 9) | Scenario 1 |
| **F29** | Adversarial Coverage Hardening | Fuzzing, boundary stress, zero-gap verification | 5 | 5 | Yes (Combo 10) | Scenario 6 |
| **TOTAL**| **29 Features** | | **145** | **145** | **10 Combos** | **6 Scenarios** |

Total Automated Test Cases: **306 test cases**.

---

## 3. Test Methodology & Derivation Techniques

The test framework applies four formal testing methodologies:

### A. Category-Partition Method
Each feature's input domain is partitioned into equivalence categories:
- **Image Input Category**: Clean RGB JPEG/PNG, WebP, Grayscale, Corrupted header, Truncated body, Giant dimensions (8000x8000), 1x1 Microscopic, Zero bytes.
- **Faces Present Category**: Exactly 1 face, Zero faces (scenery/texture), 2+ faces (crowd), Low confidence face (<0.3).
- **Network / Remote Category**: Nominal 200 OK with valid JPEG, 403 Forbidden, 404 Not Found, 504 Gateway Timeout, Rate Limited (429), Malformed non-image payload.
- **EVM Query Category**: Unrecorded hash, Valid recorded hash, Re-record duplicate hash, Zero hash (`0x00...00`), Non-hex string, Odd-length hex string.

### B. Boundary Value Analysis (BVA)
Boundary conditions tested across critical interfaces:
- **Cosine Similarity Range**: $S \in [-1.0, 1.0] \rightarrow \text{calibrated } [0.0\%, 100.0\%]$.
  - Exact match: identical vectors $\cos(\theta) = 1.0 \rightarrow 100\%$.
  - Orthogonal: $\cos(\theta) = 0.0 \rightarrow 50\%$.
  - Exact opposite: $\cos(\theta) = -1.0 \rightarrow 0\%$.
  - Division by zero safety: zero vector $\|v\| = 0$ handled without crash.
- **EVM `bytes32` Hex Length**:
  - Valid: exactly 66 characters (`0x` followed by 64 hex characters).
  - Invalid boundaries: 65 chars (31.5 bytes), 67 chars (32.5 bytes), 0 chars (`""`), `"0x"`, `"0x" + "0"*63`.
- **RFC 8785 Canonical Serialization**:
  - Key sorting: `image_sha256` < `source_url` < `timestamp` < `title`.
  - Whitespace: strict zero whitespace between tokens.
  - Number formats: integer epoch seconds, no floating point scientific notation.
- **Byte Divergence Boundaries**:
  - Index 0 mutation (first byte).
  - Index $N-1$ mutation (last byte).
  - No mutation (identical bytes).
  - Complete replacement.

### C. Pairwise Combinatorial Testing
Interaction matrix between core pipeline components:
1. **Intake $\times$ Face Detection**: Valid image with 1 face -> crops valid face bounding box.
2. **Detection $\times$ Validation**: 0 faces -> triggers early halt; >1 faces -> generates warning payload with multi-face count.
3. **Face Embedding $\times$ Visual Search**: 512-d ArcFace vector -> feeds candidate ranker -> compares against candidate images.
4. **Search Provider $\times$ Ingestion Resilience**: HTTP 403 error on candidate 1 does not abort search; candidate 2 is successfully parsed and ranked.
5. **Top Match $\times$ Provenance Fingerprint**: Discovered match metadata + raw image bytes -> generates deterministic canonical JSON -> hashes to EVM bytes32.
6. **Provenance Fingerprint $\times$ Blockchain Contract**: EVM bytes32 submitted to `TraceProof.sol` -> returns transaction receipt and emits `EvidenceRecorded`.
7. **Blockchain Verification $\times$ UI Inspector**: `verifyEvidence` call returns `exists=true, timestamp=T` -> feeds State 4 Proof Inspector component.
8. **Original Content $\times$ Mutated Content**: Original image + 1-byte mutated clone -> `/api/tamper-check` reveals byte offset and on-chain verification failure (`CONTENT MODIFIED / UNVERIFIED`).
9. **Streaming Pipeline $\times$ UI Progress Tracker**: Multi-stage SSE emits events sequentially (intake -> scan -> search -> match -> fingerprint -> proof).
10. **Design System $\times$ Typography**: Verifies color codes, serif typography, and Devanagari branding ("चेहरा → सबूत") across all UI templates.

### D. Real-World Workload Testing
Realistic end-to-end scenarios executing multi-step investigation journeys with real artifacts, error recoveries, and adversarial challenges.

---

## 4. Test Harness Directory Layout

```
tests/
├── e2e_runner.py                # Standalone CLI test runner (--tier, --json, --verbose)
├── conftest.py                  # Pytest fixtures, test environment setup & oracles
├── test_tier1_features.py       # Tier 1: 145+ Feature coverage tests (F01 - F29)
├── test_tier2_boundaries.py     # Tier 2: 145+ Boundary & corner case tests (F01 - F29)
├── test_tier3_combinations.py   # Tier 3: Cross-feature pairwise interactions (Combos 1 - 10)
├── test_tier4_scenarios.py      # Tier 4: Real-world digital investigation workflows (Scenarios 1 - 6)
└── fixtures/                    # Deterministic test artifacts
    ├── create_fixtures.py       # Fixture generator script
    ├── clean_portrait.png       # Standard single-face portrait
    ├── clean_portrait.jpg       # Standard JPEG portrait
    ├── multi_face_portrait.png  # Multi-face image (2 faces)
    ├── multi_face_portrait.jpg  # Multi-face JPEG
    ├── non_face_pattern.png     # Geometric noise without human face
    ├── non_face_pattern.jpg     # JPEG non-face pattern
    ├── tampered_clone.png       # Clean portrait with 1 modified byte/pixel
    ├── tampered_clone.jpg       # Tampered JPEG clone
    ├── corrupted_image.bin      # Corrupt truncated binary stream
    └── metadata_sample.json     # Sample RFC 8785 metadata
```

---

## 5. Execution Modes & CLI

The test framework can be executed via pytest or via the custom `e2e_runner.py`:

```bash
# Run all tiers with standard progress
python3 tests/e2e_runner.py

# Run specific tier
python3 tests/e2e_runner.py --tier 1
python3 tests/e2e_runner.py --tier 2
python3 tests/e2e_runner.py --tier 3
python3 tests/e2e_runner.py --tier 4
python3 tests/e2e_runner.py --tier 1,2

# Structured JSON output for CI pipelines
python3 tests/e2e_runner.py --json

# Verbose output with individual test reporting
python3 tests/e2e_runner.py --verbose

# Run directly with pytest
pytest tests/ -v
```

---

## 6. Exit Code Protocol

- **Exit Code 0**: 100% of executed tests passed successfully.
- **Exit Code 1**: One or more test assertions failed, or an unhandled exception occurred during execution.

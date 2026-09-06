<div align="center">

![TRACE Banner](docs/assets/trace_hero_banner.svg)

# TRACE
### चेहरा → सबूत · DISCOVER · VERIFY · PROVE

[![Solidity](https://img.shields.io/badge/Solidity-0.8.24-F7E000?style=for-the-badge&logo=solidity&logoColor=black)](contracts/contracts/TraceProof.sol)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-05472A?style=for-the-badge&logo=fastapi&logoColor=F7E000)](backend/)
[![Next.js](https://img.shields.io/badge/Next.js-14_App_Router-FF0A87?style=for-the-badge&logo=next.js&logoColor=white)](frontend/)
[![InsightFace](https://img.shields.io/badge/InsightFace-ArcFace_512d-082F1C?style=for-the-badge&logo=python&logoColor=F7E000)](backend/app/ml/)
[![Polygon](https://img.shields.io/badge/Polygon-Amoy_Testnet-7B3FE4?style=for-the-badge&logo=polygon&logoColor=white)](https://amoy.polygonscan.com/)

**A Digital Investigation & Content Provenance Tool**  
*Built for Hackers House Goa 2026 — Task 3: Face Identification & Blockchain Verification*

📦 **GitHub Repository:** [https://github.com/imnottaken/trace](https://github.com/imnottaken/trace)

---

</div>

## 📌 Core Conceptual Distinction

> **WEB SEARCH DISCOVERS CONTENT.**  
> **FACE RECOGNITION VERIFIES VISUAL MATCH.**  
> **BLOCKCHAIN PROVES CONTENT INTEGRITY.**

TRACE is built with a strict digital forensics framing. It **never claims to identify the real-world legal identity or personal name of an individual**. Instead, it:
1. Detects facial geometry and projects faces into a 512-dimensional Euclidean feature space.
2. Performs reverse visual search over public search indices (Google Lens & Bing Visual Search).
3. Downloads discovered candidates, computes pairwise cosine similarity, and isolates high-confidence matches.
4. Generates deterministic RFC 8785 canonical JSON composite hashes.
5. Notarizes content provenance onto an immutable EVM smart contract (`TraceProof.sol`) on Polygon Amoy / Ethereum.
6. Verifies tamper resistance with bit-for-bit integrity re-queries.

---

## 🏛️ Pipeline Architecture

![TRACE Pipeline Architecture](docs/assets/pipeline_architecture.svg)

### The 7-Stage Provenance Loop:

```
[01. UPLOAD IMAGE] ──────────► Sub-pixel alignment & pre-flight inspection
       │
       ▼
[02. FACE SCAN] ────────────► SCRFD Detection + 512-d ArcFace Unit Vector
       │
       ▼
[03. CATBOX INGESTION] ──────► Ephemeral raw binary hosting for Google Lens crawler
       │
       ▼
[04. GOOGLE LENS SEARCH] ────► SerpAPI reverse search with safe="active" & domain safety filters
       │
       ▼
[05. VISUAL MATCH] ─────────► Anti-hotlinking candidate download + Lanczos upscaled ArcFace cosine rank
       │
       ▼
[06. CONTENT FINGERPRINT] ──► SHA-256 binary hash + RFC 8785 canonical composite digest
       │
       ▼
[07. ON-CHAIN NOTARIZATION] ► Immutable Proof registration in TraceProof.sol (EVM / Polygon Amoy)
       │
       ▼
[08. TAMPER AUDIT] ─────────► On-chain cryptographic lookup & bit-for-bit integrity validation
```

---

## 🎨 Visual Design System (Goa Poster Forensics)

The user interface deliberately rejects generic SaaS dashboards, purple glassmorphism, and boilerplate crypto templates. It is inspired by **contemporary Goan screen-printed street posters** mixed with digital forensics terminal tooling:

| Token | Hex Code | Visual Role |
|---|---|---|
| **Goa Green** | `#05472A` / `#006B3C` | Deep canvas & background environment |
| **Sunflower Yellow** | `#F7E000` | Primary typography, highlights & action triggers |
| **Hot Pink** | `#FF0A87` | Forensics annotations, active states & warnings |
| **Ink** | `#082F1C` | Dark screen-print borders & evidence containers |
| **Cream** | `#F5E7A1` | Metadata receipts, data badges & subheadings |

### Viewport-Fit Architecture
The entire investigation cockpit is engineered as a **100% non-scrollable, viewport-fit layout** (`h-screen overflow-hidden`). All timeline stages, candidate previews, confidence scores, transaction hashes, and tamper verification blocks fit dynamically within the screen height without layout shifts.

---

## 🔬 Core Engineering Innovations

### 1. Google Lens Ingestion via Ephemeral Catbox Proxy
Google Lens requires public image URLs for visual feature extraction. To allow arbitrary local image uploads:
- The backend ephemerally registers image bytes via `catbox.moe` API (`https://catbox.moe/user/api.php`).
- The unblocked direct binary link is supplied to SerpAPI's `google_lens` engine.
- Results are retrieved directly from Google's reverse index with zero mock data.

### 2. Multi-Layer Domain & NSFW Content Filter
Search engines often return scraper spam, adult websites, or NSFW subreddit links for portrait queries. TRACE enforces a multi-tier safety pipeline (`backend/app/search/domain_filter.py`):
- **SafeSearch**: Queries Google Lens with `safe="active"`.
- **Domain Blacklist**: Blocks 50+ adult domains and scraper networks.
- **Subreddit Filtering**: Intercepts Reddit URLs and filters out adult subreddits (`r/gonewild`, `r/nsfw`, `r/RealGirls`, etc.).
- **Social & News Whitelist**: Prioritizes verified platforms (Instagram, Reddit, X/Twitter, Wikipedia, LinkedIn, YouTube, news portals).

### 3. Instagram & Walled-Garden Fallback Pipeline
Social platforms like Instagram block direct bot image downloads (`403 Forbidden` / anti-hotlinking):
- TRACE detects hotlink-protected sources and automatically falls back to **Google's cached thumbnail proxy** (`encrypted-tbn0.gstatic.com`).
- Low-resolution thumbnails undergo **Lanczos sub-pixel upscaling** before being passed to the SCRFD detector.
- Ensures social media discoveries are successfully matched without 403 download failures.

### 4. Event-Accurate Telemetry & Diagnostics
Instead of misleading generic errors, TRACE returns granular event codes and explanations:
- `MATCH_CONFIRMED`: Face matched with similarity score $\ge 60\%$.
- `LOW_CONFIDENCE_MATCH`: Candidates found but below threshold.
- `ALL_RESULTS_BLOCKED_BY_SAFETY`: Sources found were blocked by NSFW/safety filter.
- `NO_USABLE_CANDIDATE_IMAGES`: Source pages found but image hotlinking prevented downloads.
- `NO_CANDIDATE_FACES_DETECTED`: External images did not contain detectable faces.
- `TAMPER_DETECTED`: Re-uploaded content hash mismatch vs. blockchain record.

### 5. Face ML Engine (`backend/app/ml/`)
- **Detection**: SCRFD (Sample and Computation Redistribution for Face Detection) with 5-point facial landmark alignment.
- **Embedding**: 512-dimensional ArcFace unit-normalized vectors ($\|v\|_2 = 1.0 \pm 1e-4$).
- **Calibrated Similarity**:
  $$\text{Cosine Similarity} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$
  $$\text{Calibrated Match Score} = \max\left(0.0, \min\left(100.0, \frac{\text{sim} - 0.2}{0.8} \times 100\right)\right)$$

### 6. RFC 8785 Canonical JSON Fingerprinting (`backend/app/blockchain/fingerprint.py`)
Deterministic composite digests guarantee **100% byte-for-byte reproducibility** between Python and TypeScript:
```json
{"image_sha256":"fe5a127a...","source_url":"https://example.com/post","timestamp":1788653519,"title":"Source Title"}
```

### 7. Immutable Smart Contract (`contracts/contracts/TraceProof.sol`)
- Deployed on local Hardhat chain (`31337`) and Polygon Amoy testnet.
- Packed EVM storage struct: `contentHash`, `sourceReference`, `timestamp`, `blockNumber`, `recordedBy`.
- Write-once security: duplicate registration reverts with `EvidenceAlreadyExists`.
- Fully tested with 96 Hardhat test suites passing.

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/imnottaken/trace.git
cd trace
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Edit `.env` with your API keys:
```env
SEARCH_PROVIDER=serpapi
SERPAPI_API_KEY=your_serpapi_key_here
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
```

### 3. Start Local EVM Blockchain & Deploy Contract
```bash
# Terminal 1: Start local node
cd contracts
npm install
npx hardhat node

# Terminal 2: Deploy TraceProof.sol
cd contracts
npx hardhat run scripts/deploy.ts --network localhost
```

### 4. Start FastAPI Backend Server
```bash
# Terminal 3: Launch FastAPI
cd ..
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start Next.js Frontend UI
```bash
# Terminal 4: Launch Frontend
cd frontend
npm install
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 📦 Monorepo Structure

```
trace/
├── backend/                      # Python FastAPI application
│   ├── app/
│   │   ├── main.py               # API routes & orchestration (/api/trace, /api/tamper-check)
│   │   ├── config.py             # Pydantic settings & env validation
│   │   ├── ml/
│   │   │   ├── face_engine.py    # InsightFace & ONNX ArcFace 512-d engine
│   │   │   └── weights_loader.py # Model downloader & cache manager
│   │   ├── search/
│   │   │   ├── providers.py      # Google Lens (SerpAPI) + Catbox ephemeral upload + Bing
│   │   │   ├── domain_filter.py  # NSFW & adult domain filter + social prioritization
│   │   │   └── candidate_matcher.py # Thumbnail fallback & cosine similarity ranking
│   │   └── blockchain/
│   │       ├── fingerprint.py    # RFC 8785 deterministic SHA-256 generator
│   │       ├── chain_service.py  # Web3.py EVM contract interface
│   │       └── abi/TraceProof.json
│   └── requirements.txt
│
├── frontend/                     # Next.js 14 App Router
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # 100% viewport-fit investigation dashboard
│   │   │   ├── layout.tsx        # Next fonts & poster metadata
│   │   │   └── globals.css       # Goa poster styling & tokens
│   │   ├── components/
│   │   │   ├── TraceLogo.tsx
│   │   │   ├── UploadZone.tsx
│   │   │   ├── InvestigationTimeline.tsx
│   │   │   ├── MatchComparison.tsx
│   │   │   ├── FingerprintDisplay.tsx
│   │   │   ├── BlockchainProof.tsx
│   │   │   ├── VerificationResult.tsx
│   │   │   └── TamperCheck.tsx
│   │   └── lib/
│   │       └── api.ts            # Typed client SDK
│   └── tailwind.config.ts
│
├── contracts/                    # Solidity smart contracts
│   ├── contracts/
│   │   └── TraceProof.sol        # Immutable evidence registry
│   ├── test/                     # 96 Hardhat & adversarial test cases
│   ├── scripts/deploy.ts         # Multi-network deployment script
│   └── hardhat.config.ts         # Localhost & Polygon Amoy setup
│
├── docs/assets/                  # Vector illustrations & diagrams
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔒 Privacy & Limitations Disclaimer

- **Proof of Concept**: Built for Hackers House Goa 2026.
- **Biometric Protection**: Facial embeddings are computed in-memory during investigation and are never persisted in a permanent biometric database.
- **Forensic Scope**: TRACE is designed for content provenance, visual copyright verification, and source attribution — not autonomous surveillance or mass profiling.

---

<div align="center">
  <sub>Built with ❤️ for <b>Hackers House Goa 2026</b></sub>
</div>

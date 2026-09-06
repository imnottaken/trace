# Original User Request

## 2026-09-05T18:57:09Z

TRACE (चेहरा → सबूत · DISCOVER · VERIFY · PROVE) is a digital investigation and content provenance application for HH Goa 2026 Shortlisting Task 3: "Face Identification & Blockchain Verification".

Working directory: /Users/koustavdey/hhgoaface
Integrity mode: development

The user requested the full multi-agent teamwork system to build the entire project end-to-end across frontend, backend/ML, search integration, blockchain, and QA.

## Requirements

### R1. Goa Poster Aesthetic Frontend (Next.js + Tailwind + Framer Motion)
- A non-generic, high-impact editorial UI inspired by Goan/Indian screen-printed posters with digital forensics elements.
- **Palette**: Deep Goa green (`#006B3C` / `#05472A`), warm sunflower yellow (`#F7E000`), hot pink accent (`#FF0A87`), ink black-green (`#082F1C`), cream (`#F5E7A1`).
- **Typography**: High-contrast oversized editorial serif headers, condensed mono/sans UI typography, Devanagari accents ("चेहरा → सबूत").
- **Workflow Pages/States**:
  1. *Landing / Upload*: Hero, drag-and-drop file upload, "BEGIN TRACE →", how it works overlay.
  2. *Investigation Progress*: Step-by-step pipeline tracker (Face Scan → Web Discovery → Match Verification → Fingerprint → Blockchain Proof).
  3. *Match UI*: Side-by-side comparison of input vs discovered source with visual similarity score %, domain badge, source URL, "VIEW SOURCE ↗".
  4. *Proof & Blockchain UI*: Formatted SHA-256 fingerprint, block number, transaction hash, explorer link, network indicator.
  5. *Verification & Tamper Demo*: One-click re-verification of content integrity against on-chain state, plus interactive "Tamper Check" demo showing modified hash detection.

### R2. Face Detection, Embedding & Real Reverse Web Search Engine (Python / FastAPI)
- **Face Analysis**: Open-source InsightFace / ONNX Runtime stack to detect faces, extract 512-d embeddings, calculate cosine visual similarity, and reject/warn on multi-face or no-face inputs.
- **Search Provider Abstraction**: Modular `SearchProvider` interface with genuine reverse image / visual search capabilities (Google Lens / SerpAPI / Bing Visual / DuckDuckGo / web scraper), configurable via environment variables (`SEARCH_PROVIDER`, `SEARCH_API_KEY`).
- **Candidate Processing**: Download accessible candidate images, run face detection & embedding extraction, compute visual similarity against input, rank candidates, and select top matching source.
- **Zero Fake Data**: Real execution pipeline. If mock provider is included for unit testing, it must be explicitly disabled by default and clearly badged.

### R3. Content Fingerprinting & Smart Contract Provenance (Solidity + Web3)
- **Content Fingerprinting**: Deterministic SHA-256 hashing of discovered content bytes + structured provenance metadata (source URL, normalized title, timestamp).
- **Smart Contract (`TraceProof.sol`)**:
  - `recordEvidence(bytes32 contentHash, string calldata sourceReference)`
  - `getEvidence(bytes32 contentHash) external view returns (bytes32, string memory, uint256, address)`
  - `verifyEvidence(bytes32 contentHash) external view returns (bool, uint256)`
- **EVM Integration**: Web3 backend service supporting Polygon Amoy testnet / local EVM (Hardhat/Anvil/Ganache) with fallback RPC and deterministic key management via `.env`.

### R4. End-to-End Orchestration, Tamper Testing & Documentation
- **API Orchestration**: FastAPI backend providing `/api/trace` (streaming or polling pipeline), `/api/analyze-face`, `/api/search-and-match`, `/api/register-proof`, `/api/verify-proof`, and `/api/tamper-check`.
- **Tamper Demonstration Mode**: Allows re-uploading original image vs modified/edited version to demonstrate cryptographic tamper detection live.
- **Comprehensive README & Submission Pack**: Complete architecture breakdown, pipeline diagram, local setup instructions, contract deployment guide, screen recording demo workflow, and privacy/ethical limitations disclaimer.

---

## Acceptance Criteria

### Visual & UX Standards
- [ ] UI reflects the Goa poster aesthetic (deep green, sunflower yellow, hot pink, editorial serif, Devanagari branding) without generic SaaS cards, glassmorphism, or purple gradients.
- [ ] Real-time or polling investigation timeline visibly steps through Face Scan → Search → Match → Fingerprint → Proof with status indicators.
- [ ] Language strictly adheres to forensics terminology ("Face match", "Visual similarity", "Candidate source", "Content provenance", "On-chain proof") without claiming real-world personal identity.

### ML & Search Execution
- [ ] Uploading a portrait photo detects face coordinates and generates an InsightFace embedding.
- [ ] Reverse image search calls a genuine search provider, discovers external candidate URLs/images, downloads candidates, and ranks them by cosine similarity score.
- [ ] Single-face validation alerts the user appropriately if no face or multiple faces are found.

### Blockchain & Integrity
- [ ] `TraceProof.sol` compiles and deploys cleanly to EVM.
- [ ] Content hash is correctly computed and recorded on-chain via transaction.
- [ ] Verification query accurately confirms on-chain existence and returns the matching block/timestamp.
- [ ] Tampering with a single byte or modifying the test image results in an immediate `CONTENT MODIFIED / UNVERIFIED` status.

### Code Quality & Packaging
- [ ] Full monorepo structure (`frontend/`, `backend/`, `contracts/`, `scripts/`, `docs/`).
- [ ] Frontend builds cleanly with zero TypeScript errors (`npm run build`).
- [ ] Backend runs with FastAPI + Uvicorn and tests pass.
- [ ] `.env.example` provided with zero committed secrets.
- [ ] Complete `README.md` with step-by-step setup, architecture diagrams, and a 60-second screen-recording demo guide.

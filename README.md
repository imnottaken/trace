# trace

reverse face search with on-chain cryptographic provenance.

search discovers public sources -> arcface computes visual similarity -> evm contract logs the immutable proof.

demo: https://frontend-zeta-seven-zznxwxx7wg.vercel.app

---

## how it works

1. **face scan**: scrfd detects face landmarks + arcface extracts a 512-d unit embedding.
2. **web discovery**: queries google lens (via serpapi) with adult/nsfw domain filters to locate public candidate images.
3. **candidate match**: downloads discovered candidate images (with thumbnail proxy fallback for walled gardens like instagram) and ranks by cosine similarity.
4. **content fingerprint**: generates a deterministic rfc 8785 canonical sha-256 composite hash of the image bytes and source metadata.
5. **on-chain proof**: registers `(contentHash, sourceUrl, timestamp)` in `TraceProof.sol` on evm / polygon.
6. **tamper check**: allows uploading any file to verify whether its byte-level hash matches the on-chain notarization.

---

## architecture

```
image upload -> scrfd + arcface (512-d) -> google lens search -> candidate cosine rank
                                                                           │
                                                                           ▼
tamper audit <- on-chain verification <- traceproof.sol (evm) <- rfc 8785 sha-256
```

---

## stack

- **frontend**: next.js 14, typescript, tailwind css, framer-motion
- **backend**: fastapi, insightface (onnx runtime), httpx
- **smart contracts**: solidity 0.8.24, hardhat, polygon amoy / local evm

---

## local setup

### prerequisites
- node.js 18+
- python 3.11+
- git

### 1. clone & env
```bash
git clone https://github.com/imnottaken/trace.git
cd trace
cp .env.example .env
```

Add your `SERPAPI_API_KEY` to `.env`.

### 2. start local chain & deploy contract
```bash
# terminal 1: local evm node
cd contracts
npm install
npx hardhat node

# terminal 2: deploy contract
cd contracts
npx hardhat run scripts/deploy.ts --network localhost
```

### 3. run backend
```bash
# terminal 3: fastapi api server
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. run frontend
```bash
# terminal 4: next.js dev server
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## project structure

```
trace/
├── backend/                  # fastapi backend & insightface inference
│   ├── app/
│   │   ├── main.py           # api endpoints (/api/trace, /api/tamper-check)
│   │   ├── ml/               # scrfd + arcface face engine
│   │   ├── search/           # google lens search + candidate matcher
│   │   └── blockchain/       # web3.py integration + rfc 8785 hashing
│   └── requirements.txt
├── frontend/                 # next.js 14 web app
│   └── src/
│       ├── app/              # dashboard & layout
│       └── components/       # timeline, match comparison, tamper check
└── contracts/                # solidity smart contracts
    ├── contracts/TraceProof.sol
    └── test/                 # contract test suites
```

---

## license

mit

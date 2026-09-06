import { expect } from "chai";
import { ethers } from "hardhat";
import { execSync } from "child_process";
import * as path from "path";
import * as crypto from "crypto";
import { TraceProof } from "../typechain-types";
import {
  generateCompositeFingerprint,
  normalizeUrl,
  normalizeTitle,
  computeRawImageHash,
  buildCanonicalMetadata,
} from "../lib/fingerprint";

describe("Empirical Challenger 2: Two-Tier Determinism & Tamper Oracle", function () {
  this.timeout(60000);

  const backendPath = path.resolve(__dirname, "../../backend");

  function runPythonFingerprint(
    imageBytesHex: string,
    sourceUrl: string,
    title: string,
    timestamp: number
  ): {
    bytes32Hex: string;
    canonicalJson: string;
    imageSha256: string;
  } {
    const pythonScript = `
import sys, json, binascii
sys.path.insert(0, ${JSON.stringify(backendPath)})
from app.blockchain.fingerprint import generate_composite_fingerprint

raw_bytes = binascii.unhexlify(${JSON.stringify(imageBytesHex)})
url = ${JSON.stringify(sourceUrl)}
title = ${JSON.stringify(title)}
ts = ${timestamp}

b32, c_json, img_h, _ = generate_composite_fingerprint(raw_bytes, url, title, ts)
print(json.dumps({"bytes32Hex": b32, "canonicalJson": c_json, "imageSha256": img_h}))
`;
    const output = execSync("python3 -", {
      input: pythonScript,
      encoding: "utf-8",
      maxBuffer: 20 * 1024 * 1024,
    });
    return JSON.parse(output.trim());
  }

  function runPythonNormalizeUrl(rawUrl: string): string {
    const pythonScript = `
import sys, json
sys.path.insert(0, ${JSON.stringify(backendPath)})
from app.blockchain.fingerprint import normalize_url

print(json.dumps(normalize_url(${JSON.stringify(rawUrl)})))
`;
    const output = execSync("python3 -", {
      input: pythonScript,
      encoding: "utf-8",
    });
    return JSON.parse(output.trim());
  }

  // Calculate Hamming distance in bits between two 32-byte buffers
  function computeHammingDistance(bufA: Buffer, bufB: Buffer): number {
    expect(bufA.length).to.equal(32);
    expect(bufB.length).to.equal(32);
    let diffBits = 0;
    for (let i = 0; i < 32; i++) {
      let xor = bufA[i] ^ bufB[i];
      while (xor > 0) {
        diffBits += xor & 1;
        xor >>= 1;
      }
    }
    return diffBits;
  }

  // --------------------------------------------------------------------------
  // CHALLENGE 1: Byte-for-Byte TS vs Python Equivalence
  // --------------------------------------------------------------------------
  describe("Challenge 1: Cross-Language Byte-for-Byte Equivalence (TS vs Python)", function () {

    describe("1.1 Randomized Binary Inputs", function () {
      it("should produce 100% identical outputs for 28 randomized binary payloads of varying sizes", function () {
        const sizes = [
          0, 1, 2, 3, 7, 15, 16, 31, 32, 63, 64, 127, 128, 255, 256, 511, 512, 1023, 1024, 4096, 16384, 65536
        ];

        // Specific edge-case buffers
        const testBuffers: Buffer[] = [
          Buffer.alloc(0),                              // Empty buffer
          Buffer.alloc(1, 0x00),                        // Single null byte
          Buffer.alloc(1, 0xff),                        // Single 0xFF byte
          Buffer.alloc(32, 0x00),                       // 32 null bytes
          Buffer.alloc(32, 0xff),                       // 32 0xFF bytes
          Buffer.from(Array.from({ length: 256 }, (_, i) => i)), // All 256 byte values 0x00..0xFF
        ];

        // Add randomized buffers for each target size
        for (const size of sizes) {
          testBuffers.push(crypto.randomBytes(size));
        }

        // Run tests across all buffers
        for (let idx = 0; idx < testBuffers.length; idx++) {
          const buf = testBuffers[idx];
          const testUrl = `https://provenance.goa.gov.in/evidence/sample_${idx}.bin?id=${idx}`;
          const testTitle = `Randomized Forensic Binary Fixture #${idx} (${buf.length} bytes)`;
          const testTs = 1725562800 + idx * 100;

          const tsRes = generateCompositeFingerprint(buf, testUrl, testTitle, testTs);
          const pyRes = runPythonFingerprint(buf.toString("hex"), testUrl, testTitle, testTs);

          expect(tsRes.imageSha256).to.equal(pyRes.imageSha256, `imageSha256 mismatch on buffer #${idx} (len=${buf.length})`);
          expect(tsRes.canonicalJson).to.equal(pyRes.canonicalJson, `canonicalJson mismatch on buffer #${idx} (len=${buf.length})`);
          expect(tsRes.bytes32Hex).to.equal(pyRes.bytes32Hex, `bytes32Hex mismatch on buffer #${idx} (len=${buf.length})`);
        }
      });
    });

    describe("1.2 Multi-Script UTF-8 Strings and Punctuation", function () {
      const utf8Vectors = [
        {
          name: "Hindi / Devanagari (Project TRACE slogan)",
          title: "चेहरा → सबूत · डिजिटल फॉरेंसिक आणि खात्री",
          url: "https://police.goa.gov.in/forensic/case1",
        },
        {
          name: "Konkani & Marathi regional terminology",
          title: "मुखवटो वळख आनी ब्लॉकचेन पडताळणी पुरावा",
          url: "https://goa.gov.in/konkani/case2",
        },
        {
          name: "Tamil (Dravidian script)",
          title: "முக அடையாளம் மற்றும் பிளாக்செயின் சரிபார்ப்பு அறிக்கை",
          url: "https://tnpolice.gov.in/forensic/case3",
        },
        {
          name: "Japanese (Kanji, Hiragana, Katakana)",
          title: "顔認証とブロックチェーン来歴証明システム (TRACE Ver. 1.0)",
          url: "https://forensics.jp/cases/2026/case4",
        },
        {
          name: "Arabic (Right-to-Left script)",
          title: "التحقق الرقمي من الهوية الجنائية وسلسلة الكتل",
          url: "https://police.ae/forensics/case5",
        },
        {
          name: "Cyrillic (Russian / Slavic)",
          title: "Криминалистическая верификация лиц и доказательств",
          url: "https://forensic.ru/case/case6",
        },
        {
          name: "Accented Western European (French, German, Spanish)",
          title: "Preuve d'identité médico-légale & Überprüfung: ¡é, à, ü, ö, ñ, ç!",
          url: "https://interpol.int/fr/notices/case7",
        },
        {
          name: "JSON-sensitive characters (quotes, slashes, tabs, newlines)",
          title: 'Title with "double quotes", \'single quotes\', \\backslashes\\, and \t tabs',
          url: "https://test.org/path?q=quotetest",
        },
        {
          name: "Leading, trailing, and multiple internal whitespaces",
          title: "   TRACE:    Multiple    Whitespace     Test     Case   ",
          url: "https://example.com/spaced_path",
        },
      ];

      for (const vec of utf8Vectors) {
        it(`should produce 100% parity for ${vec.name}`, function () {
          const sampleBytes = Buffer.from(`PAYLOAD_UTF8_${vec.name}`);
          const ts = 1725570000;

          const tsRes = generateCompositeFingerprint(sampleBytes, vec.url, vec.title, ts);
          const pyRes = runPythonFingerprint(sampleBytes.toString("hex"), vec.url, vec.title, ts);

          expect(tsRes.imageSha256).to.equal(pyRes.imageSha256);
          expect(tsRes.canonicalJson).to.equal(pyRes.canonicalJson);
          expect(tsRes.bytes32Hex).to.equal(pyRes.bytes32Hex);
        });
      }
    });

    describe("1.3 Unicode Emojis and Complex Sequences", function () {
      const emojiVectors = [
        {
          name: "Standard forensic symbols",
          title: "Case #999 🔍: Forensic Face Evidence 📸 🛡️ ⚖️",
          emoji: "🔍📸🛡️⚖️",
        },
        {
          name: "Multi-character ZWJ sequences (family)",
          title: "Subject Photograph with Family 👨‍👩‍👧‍👦 at Goa Carnival",
          emoji: "👨‍👩‍👧‍👦",
        },
        {
          name: "Modifier sequences with skin tone",
          title: "Investigator Biometric Approval 👍🏽 and Handshake 🫱🏻‍🫲🏿",
          emoji: "👍🏽🫱🏻‍🫲🏿",
        },
        {
          name: "National flags (regional indicator pairs)",
          title: "Cross-Border Investigation 🇮🇳 India - 🇵🇹 Portugal",
          emoji: "🇮🇳🇵🇹",
        },
        {
          name: "Complex compound emojis with variation selectors",
          title: "Forensic Analyst 🕵️‍♂️ working on terminal 🧑‍💻",
          emoji: "🕵️‍♂️🧑‍💻",
        },
      ];

      for (const vec of emojiVectors) {
        it(`should produce 100% parity for emoji test: ${vec.name}`, function () {
          const sampleBytes = Buffer.from(`EMOJI_PAYLOAD_${vec.emoji}`);
          const url = `https://example.com/gallery?badge=${encodeURIComponent(vec.emoji)}`;
          const ts = 1725580000;

          const tsRes = generateCompositeFingerprint(sampleBytes, url, vec.title, ts);
          const pyRes = runPythonFingerprint(sampleBytes.toString("hex"), url, vec.title, ts);

          expect(tsRes.canonicalJson).to.equal(pyRes.canonicalJson);
          expect(tsRes.bytes32Hex).to.equal(pyRes.bytes32Hex);
        });
      }
    });

    describe("1.4 URLs with Query Parameters in Different Order", function () {
      it("should produce identical normalized URL and identical composite hash regardless of query parameter order in both TS and Python", function () {
        const urlParamOrders = [
          "https://example.com/match?alpha=1&beta=2&gamma=3&delta=4",
          "https://example.com/match?delta=4&gamma=3&beta=2&alpha=1",
          "https://example.com/match?beta=2&delta=4&alpha=1&gamma=3",
          "https://example.com/match?gamma=3&alpha=1&delta=4&beta=2",
        ];

        const sampleBytes = Buffer.from("QUERY_ORDER_INVARIANCE_TEST");
        const title = "Query Invariance Test";
        const ts = 1725590000;

        const tsFingerprints = urlParamOrders.map((url) =>
          generateCompositeFingerprint(sampleBytes, url, title, ts)
        );

        const pyFingerprints = urlParamOrders.map((url) =>
          runPythonFingerprint(sampleBytes.toString("hex"), url, title, ts)
        );

        // All TS outputs must be strictly equal across all 4 permutations
        const firstTsHash = tsFingerprints[0].bytes32Hex;
        for (let i = 1; i < tsFingerprints.length; i++) {
          expect(tsFingerprints[i].bytes32Hex).to.equal(
            firstTsHash,
            `TS hash differed for permutation ${i}`
          );
          expect(tsFingerprints[i].canonicalJson).to.equal(tsFingerprints[0].canonicalJson);
        }

        // All Python outputs must be strictly equal across all 4 permutations
        const firstPyHash = pyFingerprints[0].bytes32Hex;
        for (let i = 1; i < pyFingerprints.length; i++) {
          expect(pyFingerprints[i].bytes32Hex).to.equal(
            firstPyHash,
            `Python hash differed for permutation ${i}`
          );
          expect(pyFingerprints[i].canonicalJson).to.equal(pyFingerprints[0].canonicalJson);
        }

        // TS and Python must agree with each other
        expect(firstTsHash).to.equal(firstPyHash);
      });

      it("should strip tracking parameters (utm_*, fbclid, gclid, ref, source) identically in TS and Python", function () {
        const rawWithTracking =
          "https://example.com/news/article?utm_source=twitter&case=77&utm_medium=cpc&fbclid=1234&gclid=5678&ref=rss&source=web&page=2";
        const cleanEquivalent =
          "https://example.com/news/article?case=77&page=2";

        const tsNorm = normalizeUrl(rawWithTracking);
        const pyNorm = runPythonNormalizeUrl(rawWithTracking);
        const expectedClean = normalizeUrl(cleanEquivalent);

        expect(tsNorm).to.equal(expectedClean);
        expect(pyNorm).to.equal(expectedClean);
        expect(tsNorm).to.equal(pyNorm);
      });
    });

    describe("1.5 URLs with Default Ports (HTTP 80, HTTPS 443)", function () {
      it("should strip default port 80 for HTTP and 443 for HTTPS identically in TS and Python", function () {
        const portVectors = [
          {
            withPort: "http://example.com:80/photos/face.jpg",
            withoutPort: "http://example.com/photos/face.jpg",
          },
          {
            withPort: "https://example.com:443/photos/face.jpg",
            withoutPort: "https://example.com/photos/face.jpg",
          },
          {
            withPort: "http://ARCHIVE.ORG:80/items/case_42/",
            withoutPort: "http://archive.org/items/case_42",
          },
          {
            withPort: "https://GOA.POLICE.GOV.IN:443/evidence/?case=1",
            withoutPort: "https://goa.police.gov.in/evidence?case=1",
          },
        ];

        for (const pv of portVectors) {
          const tsNormWithPort = normalizeUrl(pv.withPort);
          const pyNormWithPort = runPythonNormalizeUrl(pv.withPort);
          const tsNormWithoutPort = normalizeUrl(pv.withoutPort);

          expect(tsNormWithPort).to.equal(tsNormWithoutPort, `TS failed to strip default port for ${pv.withPort}`);
          expect(pyNormWithPort).to.equal(tsNormWithoutPort, `Python failed to strip default port for ${pv.withPort}`);
          expect(tsNormWithPort).to.equal(pyNormWithPort, `TS vs Python mismatch for ${pv.withPort}`);
        }
      });

      it("should PRESERVE non-default ports (8080, 8443, 3000) identically in TS and Python", function () {
        const nonDefaultVectors = [
          "http://localhost:8080/api/v1/evidence",
          "https://forensics.org:8443/api/proof",
          "http://127.0.0.1:3000/app",
        ];

        for (const url of nonDefaultVectors) {
          const tsNorm = normalizeUrl(url);
          const pyNorm = runPythonNormalizeUrl(url);

          expect(tsNorm).to.equal(pyNorm, `Non-default port mismatch for ${url}`);
        }
      });
    });
  });

  // --------------------------------------------------------------------------
  // CHALLENGE 2: Cryptographic Avalanche Effect
  // --------------------------------------------------------------------------
  describe("Challenge 2: Cryptographic Avalanche Effect (Single-Bit Mutation)", function () {
    const basePayload = Buffer.from(
      "TRACE_FORENSIC_AUTHENTIC_PORTRAIT_IMAGE_RAW_BINARY_SENSOR_STREAM_PAYLOAD_HH_GOA_2026_TEST"
    );
    const sourceUrl = "https://provenance.goa.gov.in/archive/sample.png";
    const title = "Authentic Investigation Image";
    const timestamp = 1725562800;

    it("should alter bytes32 composite hash with ~50% Hamming distance for single-bit mutations", function () {
      const origFp = generateCompositeFingerprint(basePayload, sourceUrl, title, timestamp);
      const origDigest = origFp.rawDigest;

      const hammingDistances: number[] = [];
      const totalMutations = 256; // 32 bytes x 8 bits = 256 distinct 1-bit mutations

      for (let byteIdx = 0; byteIdx < 32; byteIdx++) {
        for (let bitIdx = 0; bitIdx < 8; bitIdx++) {
          const mutated = Buffer.from(basePayload);
          mutated[byteIdx] ^= (1 << bitIdx); // Flip exactly 1 bit

          const mutatedFp = generateCompositeFingerprint(mutated, sourceUrl, title, timestamp);

          // Avalanche requirement: mutated hash must NEVER equal original hash
          expect(mutatedFp.bytes32Hex).to.not.equal(
            origFp.bytes32Hex,
            `Hash collision on single-bit flip at byte ${byteIdx}, bit ${bitIdx}`
          );

          const distance = computeHammingDistance(origDigest, mutatedFp.rawDigest);
          hammingDistances.push(distance);

          // Verify individual mutation divergence: between 30% (77 bits) and 70% (179 bits)
          expect(distance).to.be.greaterThanOrEqual(
            75,
            `Hamming distance too low (${distance}/256 bits) at byte ${byteIdx}, bit ${bitIdx}`
          );
          expect(distance).to.be.lessThanOrEqual(
            180,
            `Hamming distance too high (${distance}/256 bits) at byte ${byteIdx}, bit ${bitIdx}`
          );
        }
      }

      // Calculate population statistics
      const minDistance = Math.min(...hammingDistances);
      const maxDistance = Math.max(...hammingDistances);
      const meanDistance = hammingDistances.reduce((a, b) => a + b, 0) / hammingDistances.length;
      const meanPct = (meanDistance / 256) * 100;

      console.log(`      Avalanche Effect Results over ${totalMutations} single-bit mutations:`);
      console.log(`      - Min Hamming Distance: ${minDistance} / 256 bits (${((minDistance / 256) * 100).toFixed(2)}%)`);
      console.log(`      - Max Hamming Distance: ${maxDistance} / 256 bits (${((maxDistance / 256) * 100).toFixed(2)}%)`);
      console.log(`      - Mean Hamming Distance: ${meanDistance.toFixed(2)} / 256 bits (${meanPct.toFixed(2)}%)`);

      // Statistical avalanche verification: mean Hamming distance MUST be ~50% (between 46% and 54%)
      expect(meanPct).to.be.within(
        46.0,
        54.0,
        `Cryptographic avalanche failed: mean Hamming distance was ${meanPct.toFixed(2)}%, expected ~50%`
      );
    });
  });

  // --------------------------------------------------------------------------
  // CHALLENGE 3: On-Chain Query with Tampered Hash
  // --------------------------------------------------------------------------
  describe("Challenge 3: On-Chain Contract Tamper Rejection Returns (false, 0)", function () {
    let traceProof: TraceProof;
    const genuinePayload = Buffer.from("TRACE_GENUINE_CRIMINAL_INVESTIGATION_PROOF_2026");
    const genuineUrl = "https://forensics.goa.police.gov.in/records/case_8819.jpg";
    const genuineTitle = "Genuine Evidentiary Capture Frame";
    const genuineTs = 1725562800;

    let genuineFp: ReturnType<typeof generateCompositeFingerprint>;

    beforeEach(async function () {
      const TraceProofFactory = await ethers.getContractFactory("TraceProof");
      traceProof = (await TraceProofFactory.deploy()) as unknown as TraceProof;
      await traceProof.waitForDeployment();

      genuineFp = generateCompositeFingerprint(genuinePayload, genuineUrl, genuineTitle, genuineTs);

      // Record genuine evidence on-chain
      await traceProof.recordEvidence(genuineFp.bytes32Hex, genuineFp.canonicalJson);
    });

    it("should confirm genuine registered hash returns (true, blockTimestamp)", async function () {
      const [exists, timestamp] = await traceProof.verifyEvidence(genuineFp.bytes32Hex);
      expect(exists).to.be.true;
      expect(timestamp).to.be.greaterThan(0n);
    });

    it("should return (false, 0) when queried with a 1-bit tampered image hash", async function () {
      const tamperedBytes = Buffer.from(genuinePayload);
      tamperedBytes[0] ^= 0x01; // Mutate bit 0 of byte 0

      const tamperedFp = generateCompositeFingerprint(tamperedBytes, genuineUrl, genuineTitle, genuineTs);
      expect(tamperedFp.bytes32Hex).to.not.equal(genuineFp.bytes32Hex);

      const [exists, timestamp] = await traceProof.verifyEvidence(tamperedFp.bytes32Hex);
      expect(exists).to.be.false;
      expect(timestamp).to.equal(0n);
    });

    it("should return (false, 0) when queried with a 1-character tampered source URL", async function () {
      const tamperedUrl = "https://forensics.goa.police.gov.in/records/case_8819_tampered.jpg";
      const tamperedFp = generateCompositeFingerprint(genuinePayload, tamperedUrl, genuineTitle, genuineTs);

      const [exists, timestamp] = await traceProof.verifyEvidence(tamperedFp.bytes32Hex);
      expect(exists).to.be.false;
      expect(timestamp).to.equal(0n);
    });

    it("should return (false, 0) when queried with a 1-second tampered timestamp", async function () {
      const tamperedFp = generateCompositeFingerprint(genuinePayload, genuineUrl, genuineTitle, genuineTs + 1);

      const [exists, timestamp] = await traceProof.verifyEvidence(tamperedFp.bytes32Hex);
      expect(exists).to.be.false;
      expect(timestamp).to.equal(0n);
    });

    it("should return (false, 0) when queried with a tampered title", async function () {
      const tamperedFp = generateCompositeFingerprint(genuinePayload, genuineUrl, "Tampered Title Alteration", genuineTs);

      const [exists, timestamp] = await traceProof.verifyEvidence(tamperedFp.bytes32Hex);
      expect(exists).to.be.false;
      expect(timestamp).to.equal(0n);
    });

    it("should return (false, 0) when queried with an arbitrary random 32-byte hash", async function () {
      const randomBytes32 = ethers.hexlify(crypto.randomBytes(32));

      const [exists, timestamp] = await traceProof.verifyEvidence(randomBytes32);
      expect(exists).to.be.false;
      expect(timestamp).to.equal(0n);
    });

    it("should return (false, 0) when queried with bytes32(0)", async function () {
      const zeroHash = ethers.ZeroHash;

      const [exists, timestamp] = await traceProof.verifyEvidence(zeroHash);
      expect(exists).to.be.false;
      expect(timestamp).to.equal(0n);
    });

    it("should revert with EvidenceNotFound when getEvidence is called with tampered hash", async function () {
      const tamperedBytes = Buffer.from(genuinePayload);
      tamperedBytes[0] ^= 0x80;

      const tamperedFp = generateCompositeFingerprint(tamperedBytes, genuineUrl, genuineTitle, genuineTs);

      await expect(
        traceProof.getEvidence(tamperedFp.bytes32Hex)
      )
        .to.be.revertedWithCustomError(traceProof, "EvidenceNotFound")
        .withArgs(tamperedFp.bytes32Hex);
    });

    it("should revert with EvidenceNotFound when getEvidenceDetails is called with tampered hash", async function () {
      const randomHash = ethers.hexlify(crypto.randomBytes(32));

      await expect(
        traceProof.getEvidenceDetails(randomHash)
      )
        .to.be.revertedWithCustomError(traceProof, "EvidenceNotFound")
        .withArgs(randomHash);
    });

    it("should emit EvidenceVerified(tamperedHash, false, block.timestamp) on logEvidenceVerification", async function () {
      const tamperedBytes = Buffer.from(genuinePayload);
      tamperedBytes[1] ^= 0x01;
      const tamperedFp = generateCompositeFingerprint(tamperedBytes, genuineUrl, genuineTitle, genuineTs);

      const tx = await traceProof.logEvidenceVerification(tamperedFp.bytes32Hex);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt!.blockNumber);

      await expect(tx)
        .to.emit(traceProof, "EvidenceVerified")
        .withArgs(tamperedFp.bytes32Hex, false, block!.timestamp);
    });
  });
});

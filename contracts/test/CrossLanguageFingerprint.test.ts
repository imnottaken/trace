import { expect } from "chai";
import { execSync } from "child_process";
import * as path from "path";
import {
  generateCompositeFingerprint,
  normalizeUrl,
  normalizeTitle,
  computeRawImageHash,
  buildCanonicalMetadata,
} from "../lib/fingerprint";

describe("Cross-Language Deterministic Fingerprinting (TS vs Python)", function () {
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
      maxBuffer: 10 * 1024 * 1024,
    });
    return JSON.parse(output.trim());
  }

  const testVectors = [
    {
      name: "Vector 1: Standard forensic image and news source",
      bytes: Buffer.from("SAMPLE_FORENSIC_EVIDENCE_PAYLOAD_A"),
      url: "https://timesofindia.indiatimes.com/city/goa/article/12345.cms?utm_source=twitter&id=42",
      title: "Goa Police Issue Advisory on Digital Verification",
      timestamp: 1725562800,
    },
    {
      name: "Vector 2: Devanagari Unicode and symbols in title",
      bytes: Buffer.from("DEV_TRACE_चेहरा_सबूत_FORENSIC_KEY"),
      url: "https://EXAMPLE.COM:443/forensics/face_database/?utm_medium=cpc&fbclid=tracking&case_id=987&ref=news",
      title: "  TRACE: चेहरा → सबूत · DISCOVER · VERIFY · PROVE  ",
      timestamp: 1725570000,
    },
    {
      name: "Vector 3: URL with default HTTP port 80 and uppercase host",
      bytes: Buffer.from([0x00, 0xff, 0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0]),
      url: "http://ARCHIVE.ORG:80/items/sample_portrait.png/",
      title: "High Resolution Mugshot Archive 1999",
      timestamp: 946684800,
    },
    {
      name: "Vector 4: Large binary payload (64 KB)",
      bytes: Buffer.alloc(65536, 0xaa),
      url: "https://police.gov.in/evidence/case-2026/img01.raw",
      title: "Raw Sensor Capture Frame 1042",
      timestamp: 1772841600,
    },
    {
      name: "Vector 5: Edge timestamp 0 and minimal strings",
      bytes: Buffer.from("MINIMAL"),
      url: "https://test.io/a",
      title: "Minimal Title",
      timestamp: 0,
    },
    {
      name: "Vector 6: Non-ASCII Devanagari path (Challenger failure reproduction)",
      bytes: Buffer.from("PAYLOAD_UTF8_Devanagari"),
      url: "https://police.goa.gov.in/forensic/तपास",
      title: "चेहरा → सबूत · फॉरेंसिक डिजिटल विश्लेषण",
      timestamp: 1725570000,
    },
    {
      name: "Vector 7: Non-ASCII Marathi regional path with trailing slash",
      bytes: Buffer.from("PAYLOAD_UTF8_Marathi"),
      url: "https://goa.gov.in/marathi/पुरावा/",
      title: "डिजिटल पुरावा आणि ब्लॉकचेन पडताळणी",
      timestamp: 1725570000,
    },
    {
      name: "Vector 8: Asian and Middle Eastern non-ASCII paths (Tamil, Japanese, Arabic, Cyrillic)",
      bytes: Buffer.from("PAYLOAD_MULTISCRIPT_PATHS"),
      url: "https://forensic.jp/evidence/証拠?lang=ja&case=42",
      title: "顔認識とブロックチェーン来歴証明",
      timestamp: 1725570000,
    },
    {
      name: "Vector 9: Unicode emoji symbol in URL path",
      bytes: Buffer.from("PAYLOAD_EMOJI_PATH"),
      url: "https://example.com/evidence/🔍/case-42",
      title: "Case #999 🔍: Forensic Face Evidence 📸 🛡️ ⚖️",
      timestamp: 1725580000,
    },
    {
      name: "Vector 10: Preserved percent-encoded octets and spaces in path",
      bytes: Buffer.from("PAYLOAD_PERCENT_OCTETS"),
      url: "https://archive.goa.gov.in/test%2Fencoded%20slash/mugshot 01.jpg",
      title: "Preserved Encoded Octet and Space Path Verification",
      timestamp: 1725590000,
    },
    {
      name: "Vector 11: Non-default port with non-ASCII path and unordered query parameters",
      bytes: Buffer.from("PAYLOAD_NON_DEFAULT_PORT_UNICODE"),
      url: "https://police.goa.gov.in:8443/forensic/तपास?utm_source=feed&gamma=3&alpha=1&fbclid=x&beta=2",
      title: "Complex Non-Default Port with Devanagari Slug and Query Ordering",
      timestamp: 1725600000,
    },
    {
      name: "Vector 12: Internationalized Domain Name (IDN / Punycode)",
      bytes: Buffer.from("PAYLOAD_IDN_PUNYCODE"),
      url: "https://münchen.de/path/test?tag=b&tag=a",
      title: "München Forensic Archive - Überprüfung",
      timestamp: 1725610000,
    },
    {
      name: "Vector 13: Devanagari IDN host with duplicate query params",
      bytes: Buffer.from("PAYLOAD_DEVANAGARI_IDN_DUPLICATES"),
      url: "https://चेहरा.भारत/sub?b=2&a=1&b=1",
      title: "भारत डिजिटल फॉरेंसिक रजिस्ट्री",
      timestamp: 1725620000,
    },
    {
      name: "Vector 14: IPv6 host with non-default port",
      bytes: Buffer.from("PAYLOAD_IPV6_PORT"),
      url: "http://[::1]:8080/forensic/case-42",
      title: "IPv6 Localhost Forensic Case",
      timestamp: 1725630000,
    },
  ];

  for (const vec of testVectors) {
    it(`should produce 100% identical EVM bytes32 and canonical JSON for ${vec.name}`, function () {
      const tsResult = generateCompositeFingerprint(vec.bytes, vec.url, vec.title, vec.timestamp);
      const pyResult = runPythonFingerprint(
        vec.bytes.toString("hex"),
        vec.url,
        vec.title,
        vec.timestamp
      );

      // Verify raw image sha256 equality
      expect(tsResult.imageSha256).to.equal(
        pyResult.imageSha256,
        `Raw image SHA-256 mismatch for ${vec.name}`
      );

      // Verify canonical RFC 8785 JSON string equality
      expect(tsResult.canonicalJson).to.equal(
        pyResult.canonicalJson,
        `Canonical metadata JSON mismatch for ${vec.name}`
      );

      // Verify final EVM bytes32 composite hash equality
      expect(tsResult.bytes32Hex).to.equal(
        pyResult.bytes32Hex,
        `EVM bytes32 fingerprint mismatch for ${vec.name}`
      );

      // Format sanity checks: must start with 0x and be 66 characters (32 bytes)
      expect(tsResult.bytes32Hex).to.match(/^0x[0-9a-f]{64}$/);
      expect(pyResult.bytes32Hex).to.match(/^0x[0-9a-f]{64}$/);
    });
  }

  describe("Tamper & Avalanche Effect Verification", function () {
    it("should alter composite hash significantly on single-byte change in both TS and Python", function () {
      const originalBytes = Buffer.from("AUTHENTIC_EVIDENCE_RECORD");
      const tamperedBytes = Buffer.from("AUTHENTIC_EVIDENCE_RECORe"); // 1 bit flip 'D' -> 'e'

      const url = "https://example.com/record";
      const title = "Authentic Investigation Record";
      const ts = 1725562800;

      const tsOriginal = generateCompositeFingerprint(originalBytes, url, title, ts);
      const tsTampered = generateCompositeFingerprint(tamperedBytes, url, title, ts);

      const pyOriginal = runPythonFingerprint(originalBytes.toString("hex"), url, title, ts);
      const pyTampered = runPythonFingerprint(tamperedBytes.toString("hex"), url, title, ts);

      // Confirm TS and Python both match on original
      expect(tsOriginal.bytes32Hex).to.equal(pyOriginal.bytes32Hex);

      // Confirm TS and Python both match on tampered
      expect(tsTampered.bytes32Hex).to.equal(pyTampered.bytes32Hex);

      // Confirm original vs tampered hashes diverge completely
      expect(tsOriginal.bytes32Hex).to.not.equal(tsTampered.bytes32Hex);
      expect(pyOriginal.bytes32Hex).to.not.equal(pyTampered.bytes32Hex);
    });
  });

  describe("Unicode NFC / NFD Normalization Equivalence", function () {
    it("should produce identical composite hash for NFC and NFD titles in both TS and Python", function () {
      const bytes = Buffer.from("UNICODE_NFC_NFD_TITLE_PAYLOAD");
      const url = "https://example.com/evidence/case1";
      const ts = 1725562800;

      // Latin acute: "Café" in NFC (\u00e9) vs NFD (e + \u0301)
      const nfcTitleLatin = "Caf\u00e9 Evidence Review";
      const nfdTitleLatin = "Cafe\u0301 Evidence Review";

      const tsNfcLatin = generateCompositeFingerprint(bytes, url, nfcTitleLatin, ts);
      const tsNfdLatin = generateCompositeFingerprint(bytes, url, nfdTitleLatin, ts);
      const pyNfcLatin = runPythonFingerprint(bytes.toString("hex"), url, nfcTitleLatin, ts);
      const pyNfdLatin = runPythonFingerprint(bytes.toString("hex"), url, nfdTitleLatin, ts);

      expect(tsNfcLatin.bytes32Hex).to.equal(tsNfdLatin.bytes32Hex, "TS Latin NFC vs NFD should match");
      expect(pyNfcLatin.bytes32Hex).to.equal(pyNfdLatin.bytes32Hex, "Python Latin NFC vs NFD should match");
      expect(tsNfcLatin.bytes32Hex).to.equal(pyNfcLatin.bytes32Hex, "Cross-language Latin NFC should match");

      // Devanagari nukta: "फ़ॉरेंसिक" with precomposed \u095e vs decomposed \u092b\u093c
      const nfcTitleDev = "\u095e\u0949\u0930\u0947\u0902\u0938\u093f\u0915 \u0938\u092c\u0942\u0924";
      const nfdTitleDev = "\u092b\u093c\u0949\u0930\u0947\u0902\u0938\u093f\u0915 \u0938\u092c\u0942\u0924";

      const tsNfcDev = generateCompositeFingerprint(bytes, url, nfcTitleDev, ts);
      const tsNfdDev = generateCompositeFingerprint(bytes, url, nfdTitleDev, ts);
      const pyNfcDev = runPythonFingerprint(bytes.toString("hex"), url, nfcTitleDev, ts);
      const pyNfdDev = runPythonFingerprint(bytes.toString("hex"), url, nfdTitleDev, ts);

      expect(tsNfcDev.bytes32Hex).to.equal(tsNfdDev.bytes32Hex, "TS Devanagari NFC vs NFD should match");
      expect(pyNfcDev.bytes32Hex).to.equal(pyNfdDev.bytes32Hex, "Python Devanagari NFC vs NFD should match");
      expect(tsNfcDev.bytes32Hex).to.equal(pyNfcDev.bytes32Hex, "Cross-language Devanagari NFC should match");
    });

    it("should produce identical composite hash for NFC and NFD URLs in both TS and Python", function () {
      const bytes = Buffer.from("UNICODE_NFC_NFD_URL_PAYLOAD");
      const title = "Forensic URL Normalization Test";
      const ts = 1725562800;

      const nfcUrl = "https://example.com/cases/caf\u00e9/view";
      const nfdUrl = "https://example.com/cases/cafe\u0301/view";

      const tsNfc = generateCompositeFingerprint(bytes, nfcUrl, title, ts);
      const tsNfd = generateCompositeFingerprint(bytes, nfdUrl, title, ts);
      const pyNfc = runPythonFingerprint(bytes.toString("hex"), nfcUrl, title, ts);
      const pyNfd = runPythonFingerprint(bytes.toString("hex"), nfdUrl, title, ts);

      expect(tsNfc.bytes32Hex).to.equal(tsNfd.bytes32Hex, "TS URL NFC vs NFD should match");
      expect(pyNfc.bytes32Hex).to.equal(pyNfd.bytes32Hex, "Python URL NFC vs NFD should match");
      expect(tsNfc.bytes32Hex).to.equal(pyNfc.bytes32Hex, "Cross-language URL NFC should match");
    });
  });

  describe("Duplicate Query Parameter Sorting & Permutation Invariance", function () {
    it("should sort duplicate query keys deterministically by (key, value) in both TS and Python", function () {
      const bytes = Buffer.from("QUERY_SORT_PAYLOAD");
      const title = "Query Parameter Determinism Test";
      const ts = 1725562800;

      // Duplicate key permutation
      const urlA = "https://example.com/search?tag=b&tag=a";
      const urlB = "https://example.com/search?tag=a&tag=b";

      const tsA = generateCompositeFingerprint(bytes, urlA, title, ts);
      const tsB = generateCompositeFingerprint(bytes, urlB, title, ts);
      const pyA = runPythonFingerprint(bytes.toString("hex"), urlA, title, ts);
      const pyB = runPythonFingerprint(bytes.toString("hex"), urlB, title, ts);

      expect(tsA.bytes32Hex).to.equal(tsB.bytes32Hex, "TS duplicate query params should be permutation-invariant");
      expect(pyA.bytes32Hex).to.equal(pyB.bytes32Hex, "Python duplicate query params should be permutation-invariant");
      expect(tsA.bytes32Hex).to.equal(pyA.bytes32Hex, "TS and Python should produce identical bytes32");

      // Complex multi-key duplicate permutation
      const urlComplex1 = "https://example.com/items?b=2&a=1&b=1";
      const urlComplex2 = "https://example.com/items?b=1&b=2&a=1";

      const tsComp1 = generateCompositeFingerprint(bytes, urlComplex1, title, ts);
      const tsComp2 = generateCompositeFingerprint(bytes, urlComplex2, title, ts);
      const pyComp1 = runPythonFingerprint(bytes.toString("hex"), urlComplex1, title, ts);
      const pyComp2 = runPythonFingerprint(bytes.toString("hex"), urlComplex2, title, ts);

      expect(tsComp1.bytes32Hex).to.equal(tsComp2.bytes32Hex);
      expect(pyComp1.bytes32Hex).to.equal(pyComp2.bytes32Hex);
      expect(tsComp1.bytes32Hex).to.equal(pyComp1.bytes32Hex);
    });

    it("should preserve special query characters * and ~ identically in TS and Python", function () {
      const bytes = Buffer.from("SPECIAL_QUERY_CHARS");
      const url = "https://example.com/search?q=foo*bar&q=foo~bar";
      const title = "Special Characters Query Test";
      const ts = 1725562800;

      const tsRes = generateCompositeFingerprint(bytes, url, title, ts);
      const pyRes = runPythonFingerprint(bytes.toString("hex"), url, title, ts);

      expect(tsRes.bytes32Hex).to.equal(pyRes.bytes32Hex);
      expect(tsRes.canonicalJson).to.equal(pyRes.canonicalJson);
    });
  });

  describe("URL Normalization WHATWG Parity (normalizeUrl)", function () {
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

    const urlVectors = [
      { input: "https://police.goa.gov.in/forensic/तपास", expected: "https://police.goa.gov.in/forensic/%E0%A4%A4%E0%A4%AA%E0%A4%BE%E0%A4%B8" },
      { input: "https://goa.gov.in/marathi/पुरावा/", expected: "https://goa.gov.in/marathi/%E0%A4%AA%E0%A5%81%E0%A4%B0%E0%A4%BE%E0%A4%B5%E0%A4%BE" },
      { input: "https://example.com/test%2Fencoded%20slash", expected: "https://example.com/test%2Fencoded%20slash" },
      { input: "https://example.com/tags/c%2B%2B", expected: "https://example.com/tags/c%2B%2B" },
      { input: "https://example.com/path(1)[2]^3|4", expected: "https://example.com/path(1)[2]^3|4" },
      { input: "https://example.com/spaced path/file.jpg", expected: "https://example.com/spaced%20path/file.jpg" },
      { input: "https://example.com/evidence/🔍/case-42", expected: "https://example.com/evidence/%F0%9F%94%8D/case-42" },
      { input: "http://EXAMPLE.COM:80/photos/face.jpg?utm_source=fb&q=test", expected: "http://example.com/photos/face.jpg?q=test" },
      { input: "https://police.goa.gov.in:8443/forensic/तपास?delta=4&alpha=1", expected: "https://police.goa.gov.in:8443/forensic/%E0%A4%A4%E0%A4%AA%E0%A4%BE%E0%A4%B8?alpha=1&delta=4" },
      { input: "https://münchen.de/", expected: "https://xn--mnchen-3ya.de/" },
      { input: "https://चेहरा.भारत/sub?b=2&a=1&b=1", expected: "https://xn--61b8b0av6b.xn--h2brj9c/sub?a=1&b=1&b=2" },
      { input: "http://[::1]:8080/test", expected: "http://[::1]:8080/test" },
    ];

    for (const { input, expected } of urlVectors) {
      it(`should normalize ${input} identically in TS and Python to ${expected}`, function () {
        const tsNorm = normalizeUrl(input);
        const pyNorm = runPythonNormalizeUrl(input);
        expect(tsNorm).to.equal(expected);
        expect(pyNorm).to.equal(expected);
      });
    }
  });
});

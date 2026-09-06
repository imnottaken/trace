import { expect } from "chai";
import { ethers } from "hardhat";
import { TraceProof } from "../typechain-types";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";

describe("TraceProof Empirical Adversarial & Stress Testing (Challenger M1)", function () {
  let traceProof: TraceProof;
  let signers: HardhatEthersSigner[];
  let deployer: HardhatEthersSigner;

  beforeEach(async function () {
    signers = await ethers.getSigners();
    deployer = signers[0];

    const TraceProofFactory = await ethers.getContractFactory("TraceProof");
    traceProof = (await TraceProofFactory.deploy()) as unknown as TraceProof;
    await traceProof.waitForDeployment();
  });

  describe("1. Massive String Payloads & String Boundary Testing", function () {
    it("should successfully record and retrieve a 10KB sourceReference string", async function () {
      // Generate 10KB string (10 * 1024 = 10,240 bytes)
      const targetLength = 10240;
      const baseChunk = "PROVENANCE_METADATA_CHUNK_0123456789_ABCDEF_";
      const repetitions = Math.ceil(targetLength / baseChunk.length);
      const massive10KB = baseChunk.repeat(repetitions).slice(0, targetLength);
      expect(Buffer.byteLength(massive10KB, "utf8")).to.equal(10240);

      const contentHash = ethers.keccak256(ethers.toUtf8Bytes("MASSIVE_10KB_CONTENT_HASH"));

      // Record 10KB string
      const tx = await traceProof.connect(signers[1]).recordEvidence(contentHash, massive10KB);
      const receipt = await tx.wait();
      expect(receipt?.status).to.equal(1);

      const gasUsed = receipt!.gasUsed;
      console.log(`      [Stress 10KB] Gas used for 10KB string write: ${gasUsed.toString()} gas units`);
      // 10KB is ~320 32-byte words, SSTORE costs ~20,000 per word for cold storage -> ~6.4M gas
      // EVM block gas limit is 30M, so 6.4M-7M should succeed cleanly
      expect(gasUsed).to.be.lessThan(8000000n);

      // Verify retrieval returns complete unmodified 10KB string
      const [retrievedHash, retrievedRef, ts, recordedBy] = await traceProof.getEvidence(contentHash);
      expect(retrievedHash).to.equal(contentHash);
      expect(retrievedRef.length).to.equal(10240);
      expect(retrievedRef).to.equal(massive10KB);
      expect(recordedBy).to.equal(signers[1].address);

      // Verify getEvidenceDetails also handles 10KB struct correctly
      const details = await traceProof.getEvidenceDetails(contentHash);
      expect(details.sourceReference).to.equal(massive10KB);

      // Verify verifyEvidence static call
      const [exists, verifyTs] = await traceProof.verifyEvidence(contentHash);
      expect(exists).to.be.true;
      expect(verifyTs).to.equal(ts);
    });

    it("should record strings containing Unicode, Devanagari, and adversarial injection strings", async function () {
      const adversarialStrings = [
        "चेहरा → सबूत · DISCOVER · VERIFY · PROVE · 1234567890", // Devanagari & symbols
        '<script>alert("XSS_ATTACK_VECTOR")</script>', // HTML/XSS injection
        "'; DROP TABLE evidence; --", // SQL injection payload
        "Line1\nLine2\r\nLine3\tTabbed\0EmbeddedNull", // Multi-line, control chars
        "🎉🔥🚀🛡️📸⚖️🔗🏛️", // 4-byte UTF-8 emojis
        " ", // Single whitespace
        "   \t\n   ", // Multi-whitespace string
      ];

      for (let i = 0; i < adversarialStrings.length; i++) {
        const payload = adversarialStrings[i];
        const hash = ethers.keccak256(ethers.toUtf8Bytes(`ADVERSARIAL_STRING_${i}`));

        const tx = await traceProof.connect(signers[i % signers.length]).recordEvidence(hash, payload);
        const receipt = await tx.wait();
        expect(receipt?.status).to.equal(1);

        const [rHash, rRef, , submitter] = await traceProof.getEvidence(hash);
        expect(rHash).to.equal(hash);
        expect(rRef).to.equal(payload);
        expect(submitter).to.equal(signers[i % signers.length].address);
      }
    });

    it("should strictly reject empty string (0 length) with EmptySourceReference", async function () {
      const testHash = ethers.keccak256(ethers.toUtf8Bytes("EMPTY_STRING_TEST"));
      await expect(
        traceProof.recordEvidence(testHash, "")
      ).to.be.revertedWithCustomError(traceProof, "EmptySourceReference");
    });
  });

  describe("2. Extreme Boundary Hashes (Zero, Max, Sparse, and High-Bit)", function () {
    it("should strictly reject zero byte contentHash with InvalidContentHash", async function () {
      const zeroHash = "0x0000000000000000000000000000000000000000000000000000000000000000";
      await expect(
        traceProof.connect(signers[1]).recordEvidence(zeroHash, "valid-ref")
      ).to.be.revertedWithCustomError(traceProof, "InvalidContentHash");
    });

    it("should accept and correctly manage the lowest non-zero hash (0x00...01)", async function () {
      const minHash = "0x0000000000000000000000000000000000000000000000000000000000000001";
      const tx = await traceProof.connect(signers[1]).recordEvidence(minHash, "min-hash-ref");
      const receipt = await tx.wait();
      expect(receipt?.status).to.equal(1);

      const [exists, ts] = await traceProof.verifyEvidence(minHash);
      expect(exists).to.be.true;
      expect(ts).to.be.greaterThan(0n);

      const [rHash, rRef] = await traceProof.getEvidence(minHash);
      expect(rHash).to.equal(minHash);
      expect(rRef).to.equal("min-hash-ref");
    });

    it("should accept and correctly manage the maximum hash value (0xff...ff)", async function () {
      const maxHash = "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";
      const tx = await traceProof.connect(signers[2]).recordEvidence(maxHash, "max-hash-ref");
      const receipt = await tx.wait();
      expect(receipt?.status).to.equal(1);

      const [exists, ts] = await traceProof.verifyEvidence(maxHash);
      expect(exists).to.be.true;
      expect(ts).to.be.greaterThan(0n);

      const [rHash, rRef] = await traceProof.getEvidence(maxHash);
      expect(rHash).to.equal(maxHash);
      expect(rRef).to.equal("max-hash-ref");
    });

    it("should accept high-bit set and sparse boundary hashes", async function () {
      const boundaryHashes = [
        "0x8000000000000000000000000000000000000000000000000000000000000000", // MSB set only
        "0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", // Max positive signed int
        "0x00000000000000000000000000000000000000000000000000000000000000ff", // LSB byte set
        "0x0100000000000000000000000000000000000000000000000000000000000000", // Byte 0 bit 0
        "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", // Alternating 1010
        "0x5555555555555555555555555555555555555555555555555555555555555555", // Alternating 0101
      ];

      for (let i = 0; i < boundaryHashes.length; i++) {
        const h = boundaryHashes[i];
        await traceProof.recordEvidence(h, `boundary-ref-${i}`);
        const [exists] = await traceProof.verifyEvidence(h);
        expect(exists).to.be.true;
      }

      expect(await traceProof.getTotalEvidenceCount()).to.equal(BigInt(boundaryHashes.length));
    });
  });

  describe("3. Overwrite Attacks & Immutability Under Adversarial Conditions", function () {
    const victimHash = ethers.keccak256(ethers.toUtf8Bytes("ORIGINAL_GENUINE_EVIDENCE"));
    const victimRef = "https://forensics.gov/original_evidence.jpg";

    beforeEach(async function () {
      await traceProof.connect(signers[1]).recordEvidence(victimHash, victimRef);
    });

    it("should reject overwrite attack by the same original recorder", async function () {
      await expect(
        traceProof.connect(signers[1]).recordEvidence(victimHash, "https://forensics.gov/altered_evidence.jpg")
      )
        .to.be.revertedWithCustomError(traceProof, "EvidenceAlreadyExists")
        .withArgs(victimHash);
    });

    it("should reject overwrite attack by a different malicious recorder (front-runner)", async function () {
      await expect(
        traceProof.connect(signers[2]).recordEvidence(victimHash, "https://malicious.org/hijacked.jpg")
      )
        .to.be.revertedWithCustomError(traceProof, "EvidenceAlreadyExists")
        .withArgs(victimHash);
    });

    it("should reject overwrite even when exact same sourceReference is provided", async function () {
      await expect(
        traceProof.connect(signers[2]).recordEvidence(victimHash, victimRef)
      )
        .to.be.revertedWithCustomError(traceProof, "EvidenceAlreadyExists")
        .withArgs(victimHash);
    });

    it("should preserve original evidence integrity entirely after multiple failed overwrite attempts", async function () {
      const originalEvidence = await traceProof.getEvidence(victimHash);
      const originalDetails = await traceProof.getEvidenceDetails(victimHash);

      // Multiple attackers hammer the contract with overwrite attempts
      for (let i = 2; i < 7; i++) {
        await expect(
          traceProof.connect(signers[i]).recordEvidence(victimHash, `https://attacker-${i}.com/fraud`)
        ).to.be.revertedWithCustomError(traceProof, "EvidenceAlreadyExists");
      }

      // Verify original evidence is 100% untampered
      const postEvidence = await traceProof.getEvidence(victimHash);
      const postDetails = await traceProof.getEvidenceDetails(victimHash);

      expect(postEvidence.hash).to.equal(originalEvidence.hash);
      expect(postEvidence.sourceReference).to.equal(originalEvidence.sourceReference);
      expect(postEvidence.timestamp).to.equal(originalEvidence.timestamp);
      expect(postEvidence.recordedBy).to.equal(originalEvidence.recordedBy);

      expect(postDetails.blockNumber).to.equal(originalDetails.blockNumber);
      expect(postDetails.exists).to.be.true;

      // Evidence array length must remain 1
      expect(await traceProof.getTotalEvidenceCount()).to.equal(1n);
      expect(await traceProof.getEvidenceHashAtIndex(0)).to.equal(victimHash);
    });
  });

  describe("4. Rapid Sequential Records & Multi-Account Concurrency", function () {
    it("should record 20 sequential evidences from 20 distinct accounts without state corruption", async function () {
      const recordCount = Math.min(signers.length, 20);
      const hashes: string[] = [];

      for (let i = 0; i < recordCount; i++) {
        const hash = ethers.keccak256(ethers.toUtf8Bytes(`MULTI_ACCOUNT_EVIDENCE_${i}`));
        hashes.push(hash);
        const ref = `https://investigator-${i}.org/case/${1000 + i}`;

        const tx = await traceProof.connect(signers[i]).recordEvidence(hash, ref);
        const receipt = await tx.wait();
        expect(receipt?.status).to.equal(1);
      }

      // Check total count
      const total = await traceProof.getTotalEvidenceCount();
      expect(total).to.equal(BigInt(recordCount));

      // Verify every single record matches its respective signer and order
      for (let i = 0; i < recordCount; i++) {
        const storedHash = await traceProof.getEvidenceHashAtIndex(i);
        expect(storedHash).to.equal(hashes[i]);

        const evidence = await traceProof.getEvidence(hashes[i]);
        expect(evidence.hash).to.equal(hashes[i]);
        expect(evidence.sourceReference).to.equal(`https://investigator-${i}.org/case/${1000 + i}`);
        expect(evidence.recordedBy).to.equal(signers[i].address);

        const [exists, ts] = await traceProof.verifyEvidence(hashes[i]);
        expect(exists).to.be.true;
        expect(ts).to.be.greaterThan(0n);
      }
    });

    it("should maintain constant amortized gas consumption as the registry grows", async function () {
      // Record 15 sequential items and track gas usage for each
      const gasUsageList: bigint[] = [];

      for (let i = 0; i < 15; i++) {
        const hash = ethers.keccak256(ethers.toUtf8Bytes(`GAS_SCALING_TEST_${i}`));
        const ref = "https://standard-url.org/evidence/sample.jpg";

        const tx = await traceProof.connect(signers[i % signers.length]).recordEvidence(hash, ref);
        const receipt = await tx.wait();
        gasUsageList.push(receipt!.gasUsed);
      }

      console.log(`      [Gas Scaling] 1st record gas: ${gasUsageList[0]}`);
      console.log(`      [Gas Scaling] 2nd record gas: ${gasUsageList[1]}`);
      console.log(`      [Gas Scaling] 10th record gas: ${gasUsageList[9]}`);
      console.log(`      [Gas Scaling] 15th record gas: ${gasUsageList[14]}`);

      // From the 2nd record onwards (when the dynamic array length slot is warm),
      // the gas should be virtually identical (+- a few units for SSTORE zero-to-nonzero differences)
      const gas2 = gasUsageList[1];
      const gas15 = gasUsageList[14];
      const diff = gas15 > gas2 ? gas15 - gas2 : gas2 - gas15;

      // Ensure growth is not O(N) — diff between 2nd and 15th write should be less than 5,000 gas
      expect(diff).to.be.lessThan(5000n);
    });
  });

  describe("5. Non-Existent Hashes, Empty Slots & Revert Invariants", function () {
    it("should return (false, 0) for non-existent hashes in verifyEvidence without reverting", async function () {
      const nonExistentHashes = [
        ethers.keccak256(ethers.toUtf8Bytes("DOES_NOT_EXIST_1")),
        ethers.keccak256(ethers.toUtf8Bytes("DOES_NOT_EXIST_2")),
        "0x1234567890123456789012345678901234567890123456789012345678901234",
        "0x0000000000000000000000000000000000000000000000000000000000000000", // Zero byte hash check
        "0xffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", // Max hash check
      ];

      for (const h of nonExistentHashes) {
        const [exists, timestamp] = await traceProof.verifyEvidence(h);
        expect(exists).to.be.false;
        expect(timestamp).to.equal(0n);
      }
    });

    it("should revert with EvidenceNotFound for non-existent hashes in getEvidence", async function () {
      const nonExistent = ethers.keccak256(ethers.toUtf8Bytes("GHOST_HASH"));
      await expect(
        traceProof.getEvidence(nonExistent)
      ).to.be.revertedWithCustomError(traceProof, "EvidenceNotFound").withArgs(nonExistent);
    });

    it("should revert with EvidenceNotFound for non-existent hashes in getEvidenceDetails", async function () {
      const nonExistent = ethers.keccak256(ethers.toUtf8Bytes("GHOST_HASH_DETAILS"));
      await expect(
        traceProof.getEvidenceDetails(nonExistent)
      ).to.be.revertedWithCustomError(traceProof, "EvidenceNotFound").withArgs(nonExistent);
    });

    it("should emit EvidenceVerified with false and return (false, 0) when logging unrecorded evidence", async function () {
      const unrecorded = ethers.keccak256(ethers.toUtf8Bytes("UNRECORDED_LOG_CHECK"));
      const tx = await traceProof.connect(signers[1]).logEvidenceVerification(unrecorded);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt!.blockNumber);

      await expect(tx)
        .to.emit(traceProof, "EvidenceVerified")
        .withArgs(unrecorded, false, block!.timestamp);
    });

    it("should strictly revert with Index out of bounds on array out-of-range queries", async function () {
      // Empty contract
      await expect(traceProof.getEvidenceHashAtIndex(0)).to.be.revertedWith("Index out of bounds");
      await expect(traceProof.getEvidenceHashAtIndex(100)).to.be.revertedWith("Index out of bounds");
      await expect(traceProof.getEvidenceHashAtIndex(ethers.MaxUint256)).to.be.revertedWith("Index out of bounds");

      // Add 2 items
      await traceProof.recordEvidence(ethers.keccak256(ethers.toUtf8Bytes("H1")), "ref1");
      await traceProof.recordEvidence(ethers.keccak256(ethers.toUtf8Bytes("H2")), "ref2");

      expect(await traceProof.getTotalEvidenceCount()).to.equal(2n);
      expect(await traceProof.getEvidenceHashAtIndex(0)).to.be.properHex(64);
      expect(await traceProof.getEvidenceHashAtIndex(1)).to.be.properHex(64);

      // Boundary: index == length must revert
      await expect(traceProof.getEvidenceHashAtIndex(2)).to.be.revertedWith("Index out of bounds");
      await expect(traceProof.getEvidenceHashAtIndex(3)).to.be.revertedWith("Index out of bounds");
    });
  });
});

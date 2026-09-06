import { expect } from "chai";
import { ethers } from "hardhat";
import { TraceProof } from "../typechain-types";
import { HardhatEthersSigner } from "@nomicfoundation/hardhat-ethers/signers";
import { generateCompositeFingerprint, normalizeUrl, normalizeTitle } from "../lib/fingerprint";

describe("TraceProof Smart Contract & Provenance Registry", function () {
  let traceProof: TraceProof;
  let deployer: HardhatEthersSigner;
  let investigator1: HardhatEthersSigner;
  let investigator2: HardhatEthersSigner;

  // Test evidence fixtures
  const sampleImageBytes1 = Buffer.from("TRACE_FORENSIC_EVIDENCE_SAMPLE_IMAGE_1_JPG");
  const sampleImageBytes2 = Buffer.from("TRACE_FORENSIC_EVIDENCE_SAMPLE_IMAGE_2_PNG");
  const sourceUrl1 = "https://example.com/photos/suspect_match.jpg?utm_source=twitter&id=99";
  const title1 = "Candidate Match - Goa Photo Archive";
  const timestamp1 = 1725562800;

  let fp1: ReturnType<typeof generateCompositeFingerprint>;
  let fp2: ReturnType<typeof generateCompositeFingerprint>;

  beforeEach(async function () {
    [deployer, investigator1, investigator2] = await ethers.getSigners();

    const TraceProofFactory = await ethers.getContractFactory("TraceProof");
    traceProof = (await TraceProofFactory.deploy()) as unknown as TraceProof;
    await traceProof.waitForDeployment();

    fp1 = generateCompositeFingerprint(sampleImageBytes1, sourceUrl1, title1, timestamp1);
    fp2 = generateCompositeFingerprint(sampleImageBytes2, "https://news.org/articles/123", "Discovered Press Image", 1725563000);
  });

  describe("Deployment", function () {
    it("should deploy with address and zero initial evidence count", async function () {
      const address = await traceProof.getAddress();
      expect(address).to.properAddress;

      const total = await traceProof.getTotalEvidenceCount();
      expect(total).to.equal(0n);
    });
  });

  describe("Evidence Recording (recordEvidence)", function () {
    it("should record evidence successfully and emit EvidenceRecorded event", async function () {
      const tx = await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);
      const receipt = await tx.wait();
      expect(receipt?.status).to.equal(1);

      const block = await ethers.provider.getBlock(receipt!.blockNumber);

      await expect(tx)
        .to.emit(traceProof, "EvidenceRecorded")
        .withArgs(
          fp1.bytes32Hex,
          fp1.canonicalJson,
          block!.timestamp,
          receipt!.blockNumber,
          investigator1.address
        );

      expect(await traceProof.getTotalEvidenceCount()).to.equal(1n);
      expect(await traceProof.getEvidenceHashAtIndex(0)).to.equal(fp1.bytes32Hex);
    });

    it("should prevent duplicate evidence recording and revert with EvidenceAlreadyExists", async function () {
      await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);

      await expect(
        traceProof.connect(investigator2).recordEvidence(fp1.bytes32Hex, "duplicate-attempt")
      )
        .to.be.revertedWithCustomError(traceProof, "EvidenceAlreadyExists")
        .withArgs(fp1.bytes32Hex);
    });

    it("should prevent zero hash recording and revert with InvalidContentHash", async function () {
      const zeroHash = ethers.ZeroHash;

      await expect(
        traceProof.connect(investigator1).recordEvidence(zeroHash, "valid-reference")
      ).to.be.revertedWithCustomError(traceProof, "InvalidContentHash");
    });

    it("should prevent empty source reference and revert with EmptySourceReference", async function () {
      await expect(
        traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, "")
      ).to.be.revertedWithCustomError(traceProof, "EmptySourceReference");
    });

    it("should allow multiple distinct evidence records from different investigators", async function () {
      await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);
      await traceProof.connect(investigator2).recordEvidence(fp2.bytes32Hex, fp2.canonicalJson);

      expect(await traceProof.getTotalEvidenceCount()).to.equal(2n);
      expect(await traceProof.getEvidenceHashAtIndex(0)).to.equal(fp1.bytes32Hex);
      expect(await traceProof.getEvidenceHashAtIndex(1)).to.equal(fp2.bytes32Hex);

      const ev1 = await traceProof.getEvidence(fp1.bytes32Hex);
      const ev2 = await traceProof.getEvidence(fp2.bytes32Hex);

      expect(ev1.recordedBy).to.equal(investigator1.address);
      expect(ev2.recordedBy).to.equal(investigator2.address);
    });
  });

  describe("Evidence Verification (verifyEvidence)", function () {
    it("should return (true, timestamp) for existing evidence", async function () {
      const tx = await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt!.blockNumber);

      const [exists, timestamp] = await traceProof.verifyEvidence(fp1.bytes32Hex);
      expect(exists).to.be.true;
      expect(timestamp).to.equal(BigInt(block!.timestamp));
    });

    it("should return (false, 0) for nonexistent/tampered hash without reverting", async function () {
      const nonExistentHash = ethers.keccak256(ethers.toUtf8Bytes("NON_EXISTENT_CONTENT_HASH"));

      const [exists, timestamp] = await traceProof.verifyEvidence(nonExistentHash);
      expect(exists).to.be.false;
      expect(timestamp).to.equal(0n);
    });

    it("should demonstrate cryptographic tamper detection when image bytes are altered", async function () {
      // Record genuine evidence
      await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);

      // Verify genuine content hash returns exists = true
      const [genuineExists] = await traceProof.verifyEvidence(fp1.bytes32Hex);
      expect(genuineExists).to.be.true;

      // Create tampered image by altering a single byte
      const tamperedBytes = Buffer.from(sampleImageBytes1);
      tamperedBytes[0] = tamperedBytes[0] ^ 0xff; // Flip bits in first byte

      const tamperedFp = generateCompositeFingerprint(tamperedBytes, sourceUrl1, title1, timestamp1);

      // Confirm avalanche effect produces completely different hash
      expect(tamperedFp.bytes32Hex).to.not.equal(fp1.bytes32Hex);

      // Verify tampered hash on-chain -> strictly false
      const [tamperedExists, tamperedTimestamp] = await traceProof.verifyEvidence(tamperedFp.bytes32Hex);
      expect(tamperedExists).to.be.false;
      expect(tamperedTimestamp).to.equal(0n);
    });

    it("should demonstrate cryptographic tamper detection when metadata is altered", async function () {
      await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);

      // Mutate timestamp by 1 second
      const alteredFp = generateCompositeFingerprint(sampleImageBytes1, sourceUrl1, title1, timestamp1 + 1);

      expect(alteredFp.bytes32Hex).to.not.equal(fp1.bytes32Hex);

      const [alteredExists] = await traceProof.verifyEvidence(alteredFp.bytes32Hex);
      expect(alteredExists).to.be.false;
    });
  });

  describe("Evidence Retrieval (getEvidence & getEvidenceDetails)", function () {
    it("should return exact stored fields via getEvidence", async function () {
      const tx = await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt!.blockNumber);

      const [retrievedHash, sourceRef, ts, submitter] = await traceProof.getEvidence(fp1.bytes32Hex);

      expect(retrievedHash).to.equal(fp1.bytes32Hex);
      expect(sourceRef).to.equal(fp1.canonicalJson);
      expect(ts).to.equal(BigInt(block!.timestamp));
      expect(submitter).to.equal(investigator1.address);
    });

    it("should revert with EvidenceNotFound when querying unrecorded hash via getEvidence", async function () {
      const randomHash = ethers.keccak256(ethers.toUtf8Bytes("UNREGISTERED"));

      await expect(
        traceProof.getEvidence(randomHash)
      )
        .to.be.revertedWithCustomError(traceProof, "EvidenceNotFound")
        .withArgs(randomHash);
    });

    it("should return full packed struct via getEvidenceDetails", async function () {
      const tx = await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt!.blockNumber);

      const details = await traceProof.getEvidenceDetails(fp1.bytes32Hex);

      expect(details.contentHash).to.equal(fp1.bytes32Hex);
      expect(details.sourceReference).to.equal(fp1.canonicalJson);
      expect(details.timestamp).to.equal(BigInt(block!.timestamp));
      expect(details.blockNumber).to.equal(BigInt(receipt!.blockNumber));
      expect(details.recordedBy).to.equal(investigator1.address);
      expect(details.exists).to.be.true;
    });
  });

  describe("Audit & Logging Functions", function () {
    it("should log on-chain verification receipt via logEvidenceVerification", async function () {
      await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);

      const tx = await traceProof.connect(investigator2).logEvidenceVerification(fp1.bytes32Hex);
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt!.blockNumber);

      await expect(tx)
        .to.emit(traceProof, "EvidenceVerified")
        .withArgs(fp1.bytes32Hex, true, block!.timestamp);
    });

    it("should revert if index is out of bounds in getEvidenceHashAtIndex", async function () {
      await expect(
        traceProof.getEvidenceHashAtIndex(0)
      ).to.be.revertedWith("Index out of bounds");
    });
  });

  describe("Gas Optimization Measurements", function () {
    it("should record evidence within expected gas limits (packed 5-slot storage)", async function () {
      // First transaction writes cold storage for all slots + evidence array
      const tx = await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);
      const receipt = await tx.wait();

      const gasUsed = receipt!.gasUsed;
      console.log(`      Gas used for recordEvidence (170-byte JSON): ${gasUsed.toString()} units`);

      // 170-byte string requires 6 storage slots + 5 struct slots + array slots
      // Ensure gas is strictly bounded and reasonable for cold EVM storage writes
      expect(gasUsed).to.be.lessThan(360000n);

      // Second transaction with short URL demonstrates gas reduction when string < 32 bytes (1 slot)
      // and array length slot is warm
      const shortHash = ethers.keccak256(ethers.toUtf8Bytes("SHORT_HASH_TEST"));
      const tx2 = await traceProof.connect(investigator2).recordEvidence(shortHash, "https://example.com/proof");
      const receipt2 = await tx2.wait();
      const gasUsed2 = receipt2!.gasUsed;
      console.log(`      Gas used for recordEvidence (short URL, warm array): ${gasUsed2.toString()} units`);
      expect(gasUsed2).to.be.lessThan(180000n);
    });

    it("should verify evidence via static call with minimal gas", async function () {
      await traceProof.connect(investigator1).recordEvidence(fp1.bytes32Hex, fp1.canonicalJson);

      const estimatedGas = await traceProof.verifyEvidence.estimateGas(fp1.bytes32Hex);
      console.log(`      Estimated gas for verifyEvidence: ${estimatedGas.toString()} units`);

      expect(estimatedGas).to.be.lessThan(30000n);
    });
  });
});

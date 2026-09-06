// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title TraceProof
 * @notice Digital investigation and content provenance registry for Project TRACE.
 * @dev Implements write-once, immutable on-chain evidence notarization.
 */
contract TraceProof {
    // --- Data Structures ---

    /// @dev Gas-optimized 5-slot packed storage layout:
    /// Slot 0: contentHash (32 bytes)
    /// Slot 1: sourceReference (string slot pointer/length)
    /// Slot 2: timestamp (32 bytes)
    /// Slot 3: blockNumber (32 bytes)
    /// Slot 4: recordedBy (20 bytes) + exists (1 byte) = 21 bytes <= 32 bytes
    struct Evidence {
        bytes32 contentHash;      // Slot 0: 32 bytes (SHA-256 fingerprint)
        string sourceReference;   // Slot 1: Provenance metadata / source URL
        uint256 timestamp;        // Slot 2: Block timestamp at registration
        uint256 blockNumber;      // Slot 3: Block number at registration
        address recordedBy;       // Slot 4: Submitter address (20 bytes)
        bool exists;              // Slot 4: Existence flag (1 byte, packed into Slot 4 with recordedBy)
    }

    // --- State Variables ---

    /// @notice Primary storage mapping from 32-byte content hash to Evidence record
    mapping(bytes32 => Evidence) private _evidences;

    /// @notice Ordered list of recorded content hashes for audit enumeration
    bytes32[] private _evidenceHashes;

    // --- Custom Errors ---

    error InvalidContentHash();
    error EmptySourceReference();
    error EvidenceAlreadyExists(bytes32 contentHash);
    error EvidenceNotFound(bytes32 contentHash);

    // --- Events ---

    event EvidenceRecorded(
        bytes32 indexed contentHash,
        string sourceReference,
        uint256 timestamp,
        uint256 blockNumber,
        address indexed recordedBy
    );

    event EvidenceVerified(
        bytes32 indexed contentHash,
        bool exists,
        uint256 timestamp
    );

    // --- External Write Functions ---

    /**
     * @notice Records an immutable cryptographic fingerprint and source reference.
     * @param contentHash The 32-byte SHA-256 hash of the content and metadata.
     * @param sourceReference Canonical URL or structured metadata reference.
     * @return success True if the evidence was successfully recorded.
     */
    function recordEvidence(
        bytes32 contentHash,
        string calldata sourceReference
    ) external returns (bool) {
        if (contentHash == bytes32(0)) {
            revert InvalidContentHash();
        }
        if (bytes(sourceReference).length == 0) {
            revert EmptySourceReference();
        }
        if (_evidences[contentHash].exists) {
            revert EvidenceAlreadyExists(contentHash);
        }

        _evidences[contentHash] = Evidence({
            contentHash: contentHash,
            sourceReference: sourceReference,
            timestamp: block.timestamp,
            blockNumber: block.number,
            recordedBy: msg.sender,
            exists: true
        });

        _evidenceHashes.push(contentHash);

        emit EvidenceRecorded(
            contentHash,
            sourceReference,
            block.timestamp,
            block.number,
            msg.sender
        );

        return true;
    }

    /**
     * @notice Optional state-changing verification function that logs an on-chain verification receipt.
     * @param contentHash The 32-byte content hash to verify.
     * @return exists True if the evidence exists on-chain, false otherwise.
     * @return timestamp The recording timestamp (0 if not found).
     */
    function logEvidenceVerification(
        bytes32 contentHash
    ) external returns (bool exists, uint256 timestamp) {
        Evidence storage ev = _evidences[contentHash];
        exists = ev.exists;
        timestamp = ev.timestamp;

        emit EvidenceVerified(contentHash, exists, block.timestamp);
        return (exists, timestamp);
    }

    // --- External View Functions ---

    /**
     * @notice Retrieves the primary evidence fields as specified by requirement R3.
     * @param contentHash The 32-byte content hash to query.
     * @return hash The content hash.
     * @return sourceReference The source reference string.
     * @return timestamp The block timestamp at recording.
     * @return recordedBy The address that recorded the evidence.
     */
    function getEvidence(
        bytes32 contentHash
    ) external view returns (
        bytes32 hash,
        string memory sourceReference,
        uint256 timestamp,
        address recordedBy
    ) {
        Evidence storage ev = _evidences[contentHash];
        if (!ev.exists) {
            revert EvidenceNotFound(contentHash);
        }
        return (
            ev.contentHash,
            ev.sourceReference,
            ev.timestamp,
            ev.recordedBy
        );
    }

    /**
     * @notice Checks if evidence exists and returns its timestamp without reverting.
     * @param contentHash The 32-byte content hash to check.
     * @return exists True if the evidence exists on-chain, false otherwise.
     * @return timestamp The recording timestamp (0 if not found).
     */
    function verifyEvidence(
        bytes32 contentHash
    ) external view returns (bool exists, uint256 timestamp) {
        Evidence storage ev = _evidences[contentHash];
        return (ev.exists, ev.timestamp);
    }

    /**
     * @notice Returns the full Evidence struct including block number.
     * @param contentHash The 32-byte content hash to query.
     * @return The complete Evidence struct.
     */
    function getEvidenceDetails(
        bytes32 contentHash
    ) external view returns (Evidence memory) {
        Evidence storage ev = _evidences[contentHash];
        if (!ev.exists) {
            revert EvidenceNotFound(contentHash);
        }
        return ev;
    }

    /**
     * @notice Returns total count of recorded evidence hashes.
     * @return The number of recorded evidence hashes.
     */
    function getTotalEvidenceCount() external view returns (uint256) {
        return _evidenceHashes.length;
    }

    /**
     * @notice Returns an evidence hash by its registration index for audit enumeration.
     * @param index Array index (0 <= index < getTotalEvidenceCount()).
     * @return The 32-byte content hash at the specified index.
     */
    function getEvidenceHashAtIndex(uint256 index) external view returns (bytes32) {
        require(index < _evidenceHashes.length, "Index out of bounds");
        return _evidenceHashes[index];
    }
}

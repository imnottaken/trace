"""
Blockchain service for interacting with TraceProof.sol on EVM networks.
Supports Hardhat local node and Polygon Amoy testnet.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

logger = logging.getLogger("trace.blockchain.chain_service")


class BlockchainService:
    """
    Service to interact with the TraceProof smart contract.
    Handles evidence recording, retrieval, and verification.
    """

    def __init__(
        self,
        rpc_url: str = "http://127.0.0.1:8545",
        private_key: str = "",
        contract_address: str = "",
        chain_id: int = 31337,
        abi_path: Optional[str] = None,
    ):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.contract_address = contract_address

        # Connect to EVM node
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))

        # Add POA middleware for Polygon/Amoy
        if chain_id != 31337:
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            logger.warning("Cannot connect to EVM node at %s", rpc_url)

        # Set up account from private key
        if private_key:
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            self.account = self.w3.eth.account.from_key(private_key)
            logger.info("Blockchain account: %s", self.account.address)
        else:
            self.account = None
            logger.warning("No private key provided — read-only mode")

        # Load contract ABI
        if abi_path is None:
            abi_path = os.path.join(
                os.path.dirname(__file__), "abi", "TraceProof.json"
            )

        with open(abi_path, "r") as f:
            abi_data = json.load(f)
            # Handle both raw ABI array and Hardhat artifact format
            if isinstance(abi_data, list):
                self.abi = abi_data
            elif isinstance(abi_data, dict) and "abi" in abi_data:
                self.abi = abi_data["abi"]
            else:
                self.abi = abi_data

        # Initialize contract if address provided
        self.contract = None
        if contract_address:
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=self.abi,
            )
            logger.info(
                "TraceProof contract loaded at %s on chain %d",
                contract_address,
                chain_id,
            )

    @property
    def is_connected(self) -> bool:
        """Check if connected to EVM node."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    @property
    def network_name(self) -> str:
        """Human-readable network name."""
        names = {
            31337: "Hardhat Local",
            80002: "Polygon Amoy",
            137: "Polygon Mainnet",
            1: "Ethereum Mainnet",
        }
        return names.get(self.chain_id, f"Chain {self.chain_id}")

    def _ensure_contract(self):
        """Raise if contract is not configured."""
        if self.contract is None:
            raise ValueError(
                "Contract not initialized. Set CONTRACT_ADDRESS in .env"
            )

    def _ensure_account(self):
        """Raise if no signing account is configured."""
        if self.account is None:
            raise ValueError(
                "No signing account. Set EVM_PRIVATE_KEY in .env"
            )

    def _send_transaction(self, fn) -> Dict[str, Any]:
        """Build, sign, and send a contract transaction."""
        self._ensure_account()

        nonce = self.w3.eth.get_transaction_count(self.account.address)

        tx_params = {
            "from": self.account.address,
            "nonce": nonce,
            "chainId": self.chain_id,
        }

        # Estimate gas
        try:
            gas_estimate = fn.estimate_gas(tx_params)
            tx_params["gas"] = int(gas_estimate * 1.2)  # 20% buffer
        except Exception as e:
            logger.warning("Gas estimation failed, using default: %s", e)
            tx_params["gas"] = 500000

        # Get gas price
        try:
            tx_params["gasPrice"] = self.w3.eth.gas_price
        except Exception:
            tx_params["gasPrice"] = self.w3.to_wei("30", "gwei")

        # Build and sign
        tx = fn.build_transaction(tx_params)
        signed = self.w3.eth.account.sign_transaction(tx, self.account.key)

        # Send
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return {
            "tx_hash": receipt.transactionHash.hex(),
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "status": "success" if receipt.status == 1 else "failed",
        }

    def record_evidence(
        self, content_hash_hex: str, source_reference: str
    ) -> Dict[str, Any]:
        """
        Record evidence fingerprint on-chain.

        Args:
            content_hash_hex: 0x-prefixed 32-byte hex string.
            source_reference: Source URL or metadata reference.

        Returns:
            Transaction details including tx_hash, block_number, gas_used.
        """
        self._ensure_contract()
        self._ensure_account()

        # Convert hex string to bytes32
        if content_hash_hex.startswith("0x"):
            hash_bytes = bytes.fromhex(content_hash_hex[2:])
        else:
            hash_bytes = bytes.fromhex(content_hash_hex)

        if len(hash_bytes) != 32:
            raise ValueError(f"Content hash must be 32 bytes, got {len(hash_bytes)}")

        fn = self.contract.functions.recordEvidence(hash_bytes, source_reference)
        result = self._send_transaction(fn)

        # Get block timestamp
        block = self.w3.eth.get_block(result["block_number"])
        result["timestamp"] = block.timestamp
        result["network"] = self.network_name
        result["chain_id"] = self.chain_id
        result["contract_address"] = self.contract_address

        logger.info(
            "Evidence recorded on-chain: hash=%s tx=%s block=%d",
            content_hash_hex[:18],
            result["tx_hash"][:18],
            result["block_number"],
        )

        return result

    def get_evidence(self, content_hash_hex: str) -> Dict[str, Any]:
        """
        Retrieve evidence details from blockchain.

        Returns:
            Evidence details including content_hash, source_reference, timestamp, recorded_by.
        """
        self._ensure_contract()

        if content_hash_hex.startswith("0x"):
            hash_bytes = bytes.fromhex(content_hash_hex[2:])
        else:
            hash_bytes = bytes.fromhex(content_hash_hex)

        try:
            result = self.contract.functions.getEvidence(hash_bytes).call()
            return {
                "content_hash": "0x" + result[0].hex(),
                "source_reference": result[1],
                "timestamp": result[2],
                "recorded_by": result[3],
                "exists": True,
                "network": self.network_name,
            }
        except Exception as e:
            error_msg = str(e)
            if "EvidenceNotFound" in error_msg:
                return {"exists": False, "content_hash": content_hash_hex}
            raise

    def verify_evidence(self, content_hash_hex: str) -> Dict[str, Any]:
        """
        Verify if evidence exists on-chain (non-reverting).

        Returns:
            Dictionary with exists (bool) and timestamp.
        """
        self._ensure_contract()

        if content_hash_hex.startswith("0x"):
            hash_bytes = bytes.fromhex(content_hash_hex[2:])
        else:
            hash_bytes = bytes.fromhex(content_hash_hex)

        result = self.contract.functions.verifyEvidence(hash_bytes).call()
        return {
            "exists": result[0],
            "timestamp": result[1],
            "content_hash": content_hash_hex,
            "network": self.network_name,
        }


# --- Singleton ---

_BLOCKCHAIN_SERVICE: Optional[BlockchainService] = None


def get_blockchain_service() -> BlockchainService:
    """Return or initialize the singleton BlockchainService."""
    global _BLOCKCHAIN_SERVICE
    if _BLOCKCHAIN_SERVICE is None:
        from backend.app.config import get_settings

        settings = get_settings()
        _BLOCKCHAIN_SERVICE = BlockchainService(
            rpc_url=settings.BLOCKCHAIN_RPC_URL,
            private_key=settings.EVM_PRIVATE_KEY,
            contract_address=settings.CONTRACT_ADDRESS,
            chain_id=settings.CHAIN_ID,
        )
    return _BLOCKCHAIN_SERVICE

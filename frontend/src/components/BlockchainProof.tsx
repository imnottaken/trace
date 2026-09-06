"use client";

import { motion } from "framer-motion";

interface BlockchainProofProps {
  txHash: string;
  blockNumber: number;
  network: string;
  chainId: number;
  contractAddress: string;
  timestamp: number;
  gasUsed: number;
}

function getExplorerUrl(chainId: number, txHash: string): string | null {
  switch (chainId) {
    case 80002:
      return `https://amoy.polygonscan.com/tx/0x${txHash.replace(/^0x/, "")}`;
    case 137:
      return `https://polygonscan.com/tx/0x${txHash.replace(/^0x/, "")}`;
    case 1:
      return `https://etherscan.io/tx/0x${txHash.replace(/^0x/, "")}`;
    default:
      return null;
  }
}

function truncateHash(hash: string, chars: number = 8): string {
  const clean = hash.replace(/^0x/, "");
  if (clean.length <= chars * 2) return `0x${clean}`;
  return `0x${clean.slice(0, chars)}...${clean.slice(-chars)}`;
}

export default function BlockchainProof({
  txHash,
  blockNumber,
  network,
  chainId,
  contractAddress,
  timestamp,
  gasUsed,
}: BlockchainProofProps) {
  const explorerUrl = getExplorerUrl(chainId, txHash);

  return (
    <motion.div
      className="w-full max-w-3xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <h2 className="font-display font-bold text-3xl text-trace-yellow mb-6 border-b-2 border-trace-yellow/30 pb-3">
        PROOF
      </h2>

      <div className="bg-trace-ink border-4 border-trace-yellow p-6 space-y-5">
        {/* Status */}
        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
          <span className="text-green-400 text-2xl">✓</span>
          <span className="font-display font-bold text-xl text-green-400">
            REGISTERED
          </span>
        </motion.div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              NETWORK
            </span>
            <p className="font-mono text-sm text-trace-yellow font-bold mt-1">
              {network.toUpperCase()}
            </p>
          </div>
          <div>
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              BLOCK
            </span>
            <p className="font-mono text-sm text-trace-yellow font-bold mt-1">
              {blockNumber.toLocaleString()}
            </p>
          </div>
          <div>
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              TRANSACTION
            </span>
            <p className="font-mono text-xs text-trace-cream mt-1">
              {truncateHash(txHash)}
            </p>
          </div>
          <div>
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              TIMESTAMP
            </span>
            <p className="font-mono text-xs text-trace-cream mt-1">
              {new Date(timestamp * 1000).toISOString()}
            </p>
          </div>
          <div>
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              CONTRACT
            </span>
            <p className="font-mono text-xs text-trace-cream/60 mt-1">
              {truncateHash(contractAddress)}
            </p>
          </div>
          <div>
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              GAS USED
            </span>
            <p className="font-mono text-xs text-trace-cream/60 mt-1">
              {gasUsed.toLocaleString()}
            </p>
          </div>
        </div>

        {/* Explorer link */}
        {explorerUrl && (
          <a
            href={explorerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-4 font-mono text-sm font-bold text-trace-pink underline hover:text-trace-yellow transition-colors"
          >
            VIEW ON-CHAIN PROOF ↗
          </a>
        )}
      </div>
    </motion.div>
  );
}

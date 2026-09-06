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
  return (
    <motion.div
      className="w-full max-w-4xl mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="border-b-3 border-trace-yellow pb-3 mb-6">
        <h2 className="font-display font-black text-2xl sm:text-3xl text-trace-yellow uppercase tracking-tight">
          ON-CHAIN PROVENANCE NOTARIZATION
        </h2>
      </div>

      <div className="bg-trace-ink border-3 border-trace-yellow p-6 sm:p-8 shadow-[8px_8px_0px_#082F1C]">
        {/* Status Header */}
        <div className="flex items-center justify-between border-b border-trace-yellow/20 pb-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="w-4 h-4 bg-green-400 rounded-full inline-block animate-pulse" />
            <span className="font-display font-bold text-xl sm:text-2xl text-green-400 uppercase tracking-wide">
              IMMUTABLE EVIDENCE RECORDED
            </span>
          </div>
          <span className="bg-trace-yellow text-trace-ink font-mono font-black text-xs px-3 py-1 uppercase shadow-[2px_2px_0px_#082F1C]">
            {network}
          </span>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-trace-green/40 p-4 border border-trace-yellow/30 shadow-[3px_3px_0px_#082F1C]">
            <span className="font-mono text-[10px] text-trace-yellow/60 font-bold uppercase tracking-wider block">
              BLOCK NUMBER
            </span>
            <p className="font-mono text-xl font-black text-trace-yellow mt-1">
              #{blockNumber.toLocaleString()}
            </p>
          </div>

          <div className="bg-trace-green/40 p-4 border border-trace-yellow/30 shadow-[3px_3px_0px_#082F1C]">
            <span className="font-mono text-[10px] text-trace-yellow/60 font-bold uppercase tracking-wider block">
              GAS CONSUMED
            </span>
            <p className="font-mono text-xl font-black text-trace-yellow mt-1">
              {gasUsed.toLocaleString()}
            </p>
          </div>

          <div className="bg-trace-green/40 p-4 border border-trace-yellow/30 shadow-[3px_3px_0px_#082F1C]">
            <span className="font-mono text-[10px] text-trace-yellow/60 font-bold uppercase tracking-wider block">
              CHAIN ID
            </span>
            <p className="font-mono text-xl font-black text-trace-yellow mt-1">
              {chainId}
            </p>
          </div>

          <div className="sm:col-span-2 md:col-span-3 bg-trace-green/30 p-4 border border-trace-yellow/20 space-y-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span className="font-mono text-[10px] text-trace-cream/60 uppercase">TRANSACTION HASH</span>
              <span className="font-mono text-xs text-trace-cream font-bold">{truncateHash(txHash, 14)}</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pt-2 border-t border-trace-yellow/10">
              <span className="font-mono text-[10px] text-trace-cream/60 uppercase">CONTRACT ADDRESS</span>
              <span className="font-mono text-xs text-trace-cream/70">{contractAddress}</span>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pt-2 border-t border-trace-yellow/10">
              <span className="font-mono text-[10px] text-trace-cream/60 uppercase">NOTARIZED TIMESTAMP</span>
              <span className="font-mono text-xs text-trace-cream/70">{new Date(timestamp * 1000).toUTCString()}</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

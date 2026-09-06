"use client";

import { motion } from "framer-motion";

interface VerificationResultProps {
  localHash: string;
  onChainHash: string;
  verified: boolean;
  network: string;
  timestamp?: number;
}

export default function VerificationResult({
  localHash,
  onChainHash,
  verified,
  network,
  timestamp,
}: VerificationResultProps) {
  return (
    <motion.div
      className="w-full max-w-4xl mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="border-b-3 border-trace-yellow pb-3 mb-6">
        <h2 className="font-display font-black text-2xl sm:text-3xl text-trace-yellow uppercase tracking-tight">
          ON-CHAIN INTEGRITY CONFIRMATION
        </h2>
      </div>

      <div className="bg-trace-ink border-3 border-trace-yellow p-6 sm:p-8 shadow-[8px_8px_0px_#082F1C] space-y-6">
        {/* Hashes comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-trace-green/40 border border-trace-yellow/40 p-4 shadow-[3px_3px_0px_#082F1C]">
            <span className="font-mono text-[10px] text-trace-yellow/60 uppercase tracking-widest block font-bold">
              01. LOCAL COMPUTED DIGEST
            </span>
            <p className="font-mono text-xs text-trace-cream mt-2 break-all font-bold">
              {localHash}
            </p>
          </div>
          <div className="bg-trace-green/40 border border-trace-yellow/40 p-4 shadow-[3px_3px_0px_#082F1C]">
            <span className="font-mono text-[10px] text-trace-yellow/60 uppercase tracking-widest block font-bold">
              02. ON-CHAIN RECORDED DIGEST
            </span>
            <p className="font-mono text-xs text-trace-cream mt-2 break-all font-bold">
              {onChainHash}
            </p>
          </div>
        </div>

        {/* Big Status Badge */}
        <div
          className={`p-6 border-3 text-center shadow-[6px_6px_0px_#082F1C] ${
            verified
              ? "border-green-400 bg-green-400/15"
              : "border-trace-pink bg-trace-pink/15"
          }`}
        >
          {verified ? (
            <>
              <div className="text-green-400 font-black text-4xl sm:text-5xl mb-1">✓</div>
              <h3 className="font-display font-black text-2xl sm:text-3xl text-green-400 uppercase tracking-tight">
                CONTENT INTEGRITY CONFIRMED
              </h3>
              <p className="font-mono text-xs text-green-400/80 mt-1 uppercase tracking-wider">
                BIT-FOR-BIT MATCH WITH ON-CHAIN NOTARIZATION
              </p>
            </>
          ) : (
            <>
              <div className="text-trace-pink font-black text-4xl sm:text-5xl mb-1">⚠</div>
              <h3 className="font-display font-black text-2xl sm:text-3xl text-trace-pink uppercase tracking-tight">
                CONTENT MODIFIED / UNVERIFIED
              </h3>
              <p className="font-mono text-xs text-trace-pink/80 mt-1 uppercase tracking-wider">
                DIGEST DOES NOT MATCH ON-CHAIN EVIDENCE
              </p>
            </>
          )}
        </div>

        <div className="flex flex-col sm:flex-row justify-between items-center font-mono text-[11px] text-trace-cream/60 pt-2 border-t border-trace-yellow/10 gap-1">
          <span>NETWORK: {network.toUpperCase()}</span>
          {timestamp && timestamp > 0 && (
            <span>NOTARIZED ON: {new Date(timestamp * 1000).toUTCString()}</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

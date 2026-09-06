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
      className="w-full max-w-3xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <h2 className="font-display font-bold text-3xl text-trace-yellow mb-6 border-b-2 border-trace-yellow/30 pb-3">
        VERIFICATION
      </h2>

      <div className="space-y-6">
        {/* Hashes comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-trace-ink border-2 border-trace-yellow/30 p-4">
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              LOCAL FINGERPRINT
            </span>
            <p className="font-mono text-xs text-trace-cream mt-2 break-all">
              {localHash}
            </p>
          </div>
          <div className="bg-trace-ink border-2 border-trace-yellow/30 p-4">
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              ON-CHAIN FINGERPRINT
            </span>
            <p className="font-mono text-xs text-trace-cream mt-2 break-all">
              {onChainHash}
            </p>
          </div>
        </div>

        {/* Result */}
        <motion.div
          className={`p-6 border-4 text-center ${
            verified
              ? "border-green-400 bg-green-400/10"
              : "border-trace-pink bg-trace-pink/10"
          }`}
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", delay: 0.3 }}
        >
          {verified ? (
            <>
              <div className="text-green-400 text-4xl mb-2">✓</div>
              <h3 className="font-display font-bold text-2xl text-green-400">
                VERIFIED
              </h3>
              <p className="font-mono text-xs text-green-400/70 mt-2">
                CONTENT INTEGRITY CONFIRMED
              </p>
            </>
          ) : (
            <>
              <div className="text-trace-pink text-4xl mb-2">⚠</div>
              <h3 className="font-display font-bold text-2xl text-trace-pink">
                CONTENT MODIFIED
              </h3>
              <p className="font-mono text-xs text-trace-pink/70 mt-2">
                FINGERPRINTS DO NOT MATCH
              </p>
            </>
          )}
        </motion.div>

        {/* Meta */}
        <div className="flex justify-between items-center font-mono text-xs text-trace-yellow/40">
          <span>NETWORK: {network.toUpperCase()}</span>
          {timestamp && timestamp > 0 && (
            <span>RECORDED: {new Date(timestamp * 1000).toISOString()}</span>
          )}
        </div>
      </div>
    </motion.div>
  );
}

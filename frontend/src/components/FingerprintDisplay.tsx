"use client";

import { motion } from "framer-motion";

interface FingerprintDisplayProps {
  hash: string;
  label?: string;
  imageSha256?: string;
}

function formatHash(hash: string): string[] {
  const clean = hash.replace(/^0x/, "").toUpperCase();
  const chunks: string[] = [];
  for (let i = 0; i < clean.length; i += 8) {
    chunks.push(clean.slice(i, i + 8));
  }
  return chunks;
}

export default function FingerprintDisplay({
  hash,
  label = "CRYPTOGRAPHIC CONTENT FINGERPRINT",
  imageSha256,
}: FingerprintDisplayProps) {
  const chunks = formatHash(hash);

  return (
    <motion.div
      className="w-full max-w-4xl mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="border-b-3 border-trace-yellow pb-3 mb-6">
        <h2 className="font-display font-black text-2xl sm:text-3xl text-trace-yellow uppercase tracking-tight">
          {label}
        </h2>
      </div>

      <div className="bg-trace-ink border-3 border-trace-yellow p-6 sm:p-8 shadow-[8px_8px_0px_#082F1C]">
        <div className="flex items-center justify-between border-b border-trace-yellow/20 pb-3 mb-4">
          <span className="font-mono text-xs text-trace-pink font-bold uppercase tracking-widest">
            RFC 8785 CANONICAL DIGEST
          </span>
          <span className="font-mono text-[10px] text-trace-cream/60 bg-trace-green px-2 py-0.5 border border-trace-yellow/20">
            256-BIT SHA-256
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-2 my-4">
          {chunks.map((chunk, i) => (
            <div
              key={i}
              className="bg-trace-green/60 border border-trace-yellow/40 p-2.5 text-center shadow-[2px_2px_0px_#082F1C]"
            >
              <span className="font-mono text-xs text-trace-yellow/50 block text-[9px] mb-0.5">
                CHUNK 0{i + 1}
              </span>
              <span className="font-mono text-base font-bold text-trace-yellow tracking-wider">
                {chunk}
              </span>
            </div>
          ))}
        </div>

        {imageSha256 && (
          <div className="mt-6 pt-4 border-t border-trace-yellow/20 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
            <span className="font-mono text-xs text-trace-cream/60 uppercase tracking-wider">
              RAW IMAGE DIGEST:
            </span>
            <span className="font-mono text-xs text-trace-cream font-bold truncate max-w-lg">
              {imageSha256}
            </span>
          </div>
        )}
      </div>
    </motion.div>
  );
}

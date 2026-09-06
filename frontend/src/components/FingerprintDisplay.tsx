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
  label = "CONTENT FINGERPRINT",
  imageSha256,
}: FingerprintDisplayProps) {
  const chunks = formatHash(hash);

  return (
    <motion.div
      className="w-full max-w-3xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <h2 className="font-display font-bold text-2xl text-trace-yellow mb-4 border-b-2 border-trace-yellow/30 pb-3">
        {label}
      </h2>

      <div className="bg-trace-ink border-3 border-trace-yellow p-6">
        <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
          SHA-256
        </span>
        <div className="mt-3 flex flex-wrap gap-2">
          {chunks.map((chunk, i) => (
            <motion.span
              key={i}
              className="font-mono text-lg md:text-xl text-trace-yellow font-bold tracking-wider"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              {chunk}
            </motion.span>
          ))}
        </div>

        {imageSha256 && (
          <div className="mt-6 pt-4 border-t border-trace-yellow/20">
            <span className="font-mono text-xs text-trace-yellow/50 uppercase tracking-widest">
              IMAGE SHA-256
            </span>
            <p className="font-mono text-xs text-trace-cream/60 mt-1 break-all">
              {imageSha256}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}

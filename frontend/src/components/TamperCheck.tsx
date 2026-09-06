"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { tamperCheck, type TamperResult } from "@/lib/api";

interface TamperCheckProps {
  contentHash: string;
}

export default function TamperCheck({ contentHash }: TamperCheckProps) {
  const [file, setFile] = useState<File | null>(null);
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<TamperResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setResult(null);
      setError(null);
    }
  }, []);

  const handleCheck = useCallback(async () => {
    if (!file) return;
    setChecking(true);
    setError(null);
    try {
      const res = await tamperCheck(file, contentHash);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tamper check failed");
    } finally {
      setChecking(false);
    }
  }, [file, contentHash]);

  return (
    <motion.div
      className="w-full max-w-3xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <h2 className="font-display font-bold text-2xl text-trace-yellow mb-4 border-b-2 border-trace-yellow/30 pb-3">
        TAMPER CHECK
      </h2>
      <p className="font-mono text-xs text-trace-cream/60 mb-6">
        Upload a file to verify its integrity against the on-chain record.
      </p>

      {/* Upload */}
      <div className="flex items-center gap-4 mb-6">
        <label className="flex-1 border-2 border-dashed border-trace-yellow/50 p-4 text-center cursor-pointer hover:border-trace-pink transition-colors">
          <input
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFile}
          />
          <span className="font-mono text-sm text-trace-yellow">
            {file ? file.name : "CHOOSE FILE TO VERIFY"}
          </span>
        </label>
        <button
          onClick={handleCheck}
          disabled={!file || checking}
          className="px-6 py-4 bg-trace-yellow text-trace-ink font-mono font-bold text-sm
                     border-2 border-trace-ink hover:bg-trace-pink hover:text-white
                     transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {checking ? "CHECKING..." : "VERIFY"}
        </button>
      </div>

      {/* Comparing hash */}
      <div className="font-mono text-xs text-trace-yellow/40 mb-4">
        ON-CHAIN HASH: {contentHash.slice(0, 18)}...
      </div>

      {/* Error */}
      {error && (
        <div className="border-2 border-trace-pink p-4 mb-4">
          <span className="font-mono text-sm text-trace-pink">{error}</span>
        </div>
      )}

      {/* Result */}
      {result && (
        <motion.div
          className={`p-6 border-4 text-center ${
            !result.tampered
              ? "border-green-400 bg-green-400/10"
              : "border-trace-pink bg-trace-pink/10"
          }`}
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
        >
          {!result.tampered ? (
            <>
              <div className="text-green-400 text-4xl mb-2">✓</div>
              <h3 className="font-display font-bold text-xl text-green-400">
                VERIFIED
              </h3>
              <p className="font-mono text-xs text-green-400/70 mt-2">
                CONTENT IS AUTHENTIC
              </p>
            </>
          ) : (
            <>
              <div className="text-trace-pink text-4xl mb-2">⚠</div>
              <h3 className="font-display font-bold text-xl text-trace-pink">
                CONTENT MODIFIED
              </h3>
              <p className="font-mono text-xs text-trace-pink/70 mt-2">
                THE FILE HAS BEEN ALTERED
              </p>
            </>
          )}

          <div className="mt-4 grid grid-cols-2 gap-4 text-left">
            <div>
              <span className="font-mono text-xs text-trace-yellow/50">LOCAL</span>
              <p className="font-mono text-xs text-trace-cream break-all mt-1">
                {result.local_hash}
              </p>
            </div>
            <div>
              <span className="font-mono text-xs text-trace-yellow/50">ON-CHAIN</span>
              <p className="font-mono text-xs text-trace-cream break-all mt-1">
                {result.on_chain_hash}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}

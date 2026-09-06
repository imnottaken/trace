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
      className="w-full max-w-4xl mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="border-b-3 border-trace-yellow pb-3 mb-6">
        <h2 className="font-display font-black text-2xl sm:text-3xl text-trace-yellow uppercase tracking-tight">
          INTERACTIVE TAMPER TEST
        </h2>
      </div>

      <div className="bg-trace-ink border-3 border-trace-yellow p-6 sm:p-8 shadow-[8px_8px_0px_#082F1C]">
        <p className="font-mono text-xs text-trace-cream/80 mb-6 leading-relaxed">
          Upload any file or a modified/cropped copy of the target image to test bit-level cryptographic tamper detection against the on-chain smart contract record.
        </p>

        {/* Upload Form */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 mb-6">
          <label className="flex-1 border-2 border-dashed border-trace-yellow/60 bg-trace-green/40 p-4 text-center cursor-pointer hover:border-trace-pink transition-colors">
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFile}
            />
            <span className="font-mono text-xs sm:text-sm text-trace-yellow font-bold uppercase">
              {file ? file.name : "SELECT FILE TO VERIFY INTEGRITY"}
            </span>
          </label>
          <button
            onClick={handleCheck}
            disabled={!file || checking}
            className="px-8 py-4 bg-trace-yellow text-trace-ink font-mono font-black text-sm uppercase
                       border-3 border-trace-ink shadow-[4px_4px_0px_#082F1C] hover:bg-trace-pink hover:text-white
                       transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
          >
            {checking ? "CHECKING..." : "VERIFY INTEGRITY →"}
          </button>
        </div>

        {error && (
          <div className="border-2 border-trace-pink bg-trace-pink/10 p-4 mb-4 font-mono text-xs text-trace-pink">
            {error}
          </div>
        )}

        {result && (
          <motion.div
            className={`p-6 border-3 text-center shadow-[6px_6px_0px_#082F1C] ${
              !result.tampered
                ? "border-green-400 bg-green-400/15"
                : "border-trace-pink bg-trace-pink/15"
            }`}
            initial={{ scale: 0.95 }}
            animate={{ scale: 1 }}
          >
            {!result.tampered ? (
              <>
                <div className="text-green-400 font-black text-4xl mb-1">✓</div>
                <h3 className="font-display font-black text-xl sm:text-2xl text-green-400 uppercase tracking-tight">
                  INTEGRITY VERIFIED — EXACT MATCH
                </h3>
                <p className="font-mono text-xs text-green-400/80 mt-1 uppercase">
                  ZERO BYTES ALTERED FROM ON-CHAIN NOTARIZATION
                </p>
              </>
            ) : (
              <>
                <div className="text-trace-pink font-black text-4xl mb-1">⚠</div>
                <h3 className="font-display font-black text-xl sm:text-2xl text-trace-pink uppercase tracking-tight">
                  TAMPER DETECTED / MODIFIED CONTENT
                </h3>
                <p className="font-mono text-xs text-trace-pink/80 mt-1 uppercase">
                  THE PROVIDED FILE DIFFERS FROM THE ON-CHAIN RECORD
                </p>
              </>
            )}

            <div className="mt-6 pt-4 border-t border-trace-yellow/20 grid grid-cols-1 sm:grid-cols-2 gap-4 text-left font-mono text-xs">
              <div className="bg-trace-green/60 p-3 border border-trace-yellow/30">
                <span className="text-trace-yellow/60 block text-[10px] font-bold uppercase">UPLOADED FILE SHA-256</span>
                <p className="text-trace-cream break-all mt-1">{result.local_hash}</p>
              </div>
              <div className="bg-trace-green/60 p-3 border border-trace-yellow/30">
                <span className="text-trace-yellow/60 block text-[10px] font-bold uppercase">ON-CHAIN EVIDENCE SHA-256</span>
                <p className="text-trace-cream break-all mt-1">{result.on_chain_hash}</p>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

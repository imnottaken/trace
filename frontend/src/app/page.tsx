"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import TraceLogo from "@/components/TraceLogo";
import UploadZone from "@/components/UploadZone";
import InvestigationTimeline, { type TimelineStep } from "@/components/InvestigationTimeline";
import MatchComparison from "@/components/MatchComparison";
import FingerprintDisplay from "@/components/FingerprintDisplay";
import BlockchainProof from "@/components/BlockchainProof";
import VerificationResult from "@/components/VerificationResult";
import TamperCheck from "@/components/TamperCheck";
import { runFullTrace, type TraceResult } from "@/lib/api";

type Phase = "landing" | "investigating" | "complete" | "error";

export default function Home() {
  const [phase, setPhase] = useState<Phase>("landing");
  const [file, setFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>("");
  const [traceResult, setTraceResult] = useState<TraceResult | null>(null);
  const [error, setError] = useState<string>("");
  const [investigationId] = useState(() =>
    Math.random().toString(36).slice(2, 8).toUpperCase()
  );

  const [steps, setSteps] = useState<TimelineStep[]>([
    { id: "face", label: "Face Analysis", status: "queued" },
    { id: "search", label: "Web Discovery", status: "queued" },
    { id: "match", label: "Candidate Matching", status: "queued" },
    { id: "fingerprint", label: "Content Fingerprint", status: "queued" },
    { id: "proof", label: "Blockchain Proof", status: "queued" },
    { id: "verify", label: "Verification", status: "queued" },
  ]);

  const updateStep = useCallback(
    (id: string, status: TimelineStep["status"], detail?: string) => {
      setSteps((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status, detail } : s))
      );
    },
    []
  );

  const handleFileSelect = useCallback((f: File) => {
    setFile(f);
    setImagePreview(URL.createObjectURL(f));
  }, []);

  const handleBeginTrace = useCallback(async () => {
    if (!file) return;

    setPhase("investigating");
    setError("");

    // Animate steps sequentially
    updateStep("face", "scanning", "Detecting faces...");

    try {
      // Simulate step progression with the real API call
      // We use the full pipeline endpoint
      const stepNames = ["face", "search", "match", "fingerprint", "proof", "verify"];
      let currentStep = 0;

      // Start the actual API call
      const tracePromise = runFullTrace(file);

      // Animate steps while waiting
      const animateInterval = setInterval(() => {
        currentStep++;
        if (currentStep < stepNames.length) {
          // Mark previous as complete
          updateStep(stepNames[currentStep - 1], "complete");
          // Mark current as scanning
          const labels: Record<string, string> = {
            search: "Searching the web...",
            match: "Comparing faces...",
            fingerprint: "Computing SHA-256...",
            proof: "Submitting to blockchain...",
            verify: "Confirming on-chain...",
          };
          updateStep(
            stepNames[currentStep],
            "scanning",
            labels[stepNames[currentStep]] || "Processing..."
          );
        }
      }, 2000);

      const result = await tracePromise;
      clearInterval(animateInterval);

      if (result.success && result.result) {
        // Mark all steps complete with real data
        const r = result.result;
        updateStep("face", "complete",
          `${r.face_analysis.face_count} face(s) · ${(r.face_analysis.confidence * 100).toFixed(0)}% confidence`
        );
        updateStep("search", "complete",
          `${r.all_matches.length} candidates via ${r.search_provider}`
        );
        updateStep("match", "complete",
          `Top: ${(r.best_match.similarity_score * 100).toFixed(1)}% similarity`
        );
        updateStep("fingerprint", "complete",
          `SHA-256: ${r.fingerprint.content_hash.slice(0, 16)}...`
        );

        if (r.blockchain) {
          updateStep("proof", "complete",
            `Block #${r.blockchain.block_number} · ${r.blockchain.network}`
          );
        } else {
          updateStep("proof", "skipped", "Blockchain not configured");
        }

        if (r.verification?.exists) {
          updateStep("verify", "complete", "Content integrity confirmed");
        } else if (r.blockchain) {
          updateStep("verify", "complete", "On-chain record verified");
        } else {
          updateStep("verify", "skipped", "No blockchain record");
        }

        setTraceResult(result);
        setPhase("complete");
      } else {
        // Handle partial failure
        const failedStep = result.steps?.find((s) => s.status === "failed" || s.status === "no_results" || s.status === "no_match");
        if (failedStep) {
          const stepMap: Record<string, string> = {
            face_analysis: "face",
            web_search: "search",
            candidate_matching: "match",
            fingerprint: "fingerprint",
            blockchain_registration: "proof",
            verification: "verify",
          };
          const mappedId = stepMap[failedStep.step] || failedStep.step;
          updateStep(mappedId, "failed", result.error || "No results");
        }

        setError(result.error || "Pipeline did not complete successfully");
        setTraceResult(result);
        setPhase("error");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "An unexpected error occurred";
      setError(msg);
      // Mark current scanning step as failed
      setSteps((prev) =>
        prev.map((s) =>
          s.status === "scanning" ? { ...s, status: "failed", detail: msg } : s
        )
      );
      setPhase("error");
    }
  }, [file, updateStep]);

  const handleReset = useCallback(() => {
    setPhase("landing");
    setFile(null);
    setImagePreview("");
    setTraceResult(null);
    setError("");
    setSteps([
      { id: "face", label: "Face Analysis", status: "queued" },
      { id: "search", label: "Web Discovery", status: "queued" },
      { id: "match", label: "Candidate Matching", status: "queued" },
      { id: "fingerprint", label: "Content Fingerprint", status: "queued" },
      { id: "proof", label: "Blockchain Proof", status: "queued" },
      { id: "verify", label: "Verification", status: "queued" },
    ]);
  }, []);

  return (
    <main className="min-h-screen bg-trace-green">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 md:px-12 py-4 border-b border-trace-yellow/10">
        <div className="cursor-pointer" onClick={handleReset}>
          <TraceLogo size="small" />
        </div>
        <div className="flex gap-6">
          <button className="font-mono text-xs text-trace-yellow/60 hover:text-trace-yellow transition-colors uppercase tracking-wider">
            How It Works
          </button>
          <button className="font-mono text-xs text-trace-yellow/60 hover:text-trace-yellow transition-colors uppercase tracking-wider">
            About
          </button>
        </div>
      </nav>

      <AnimatePresence mode="wait">
        {/* === LANDING === */}
        {phase === "landing" && (
          <motion.div
            key="landing"
            className="px-6 md:px-12 py-12 md:py-24"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -30 }}
          >
            <div className="max-w-4xl mx-auto">
              <TraceLogo size="large" />

              <p className="font-mono text-sm md:text-base text-trace-cream/70 mt-8 max-w-xl leading-relaxed">
                Find where an image appears online.
                <br />
                Verify the visual match.
                <br />
                Create a tamper-evident proof.
              </p>

              <div className="mt-12">
                <UploadZone
                  onFileSelect={handleFileSelect}
                  onBeginTrace={handleBeginTrace}
                  disabled={phase !== "landing"}
                />
              </div>
            </div>
          </motion.div>
        )}

        {/* === INVESTIGATING === */}
        {(phase === "investigating" || phase === "error") && (
          <motion.div
            key="investigating"
            className="px-6 md:px-12 py-12"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <InvestigationTimeline
              steps={steps}
              investigationId={investigationId}
            />

            {/* Event-driven Status Banner */}
            {phase === "error" && error && (
              <motion.div
                className="max-w-3xl mx-auto mt-8 p-6 bg-trace-ink border-3 border-trace-pink shadow-[8px_8px_0px_#082F1C]"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-3 h-3 bg-trace-pink rounded-full inline-block animate-ping" />
                  <span className="font-mono text-xs font-bold text-trace-pink uppercase tracking-widest">
                    INVESTIGATION STATUS REPORT
                  </span>
                </div>
                <h3 className="font-display font-black text-2xl text-trace-yellow mb-2 uppercase">
                  {error.includes("safety") || error.includes("NSFW") || error.includes("adult")
                    ? "DISCOVERED SITES FILTERED BY SAFETY POLICY"
                    : error.includes("indexed")
                    ? "ZERO PUBLIC OCCURRENCES INDEXED"
                    : "INVESTIGATION NOT COMPLETED"}
                </h3>
                <p className="font-mono text-sm text-trace-cream/90 leading-relaxed bg-trace-green/40 p-4 border border-trace-yellow/20">
                  {error}
                </p>
                <div className="mt-6 flex flex-col sm:flex-row gap-4">
                  <button
                    onClick={handleReset}
                    className="px-6 py-3 bg-trace-yellow text-trace-ink font-mono font-black text-xs uppercase border-3 border-trace-ink shadow-[4px_4px_0px_#082F1C] hover:bg-trace-pink hover:text-white transition-all"
                  >
                    ← TRY ANOTHER IMAGE
                  </button>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* === COMPLETE === */}
        {phase === "complete" && traceResult?.result && (
          <motion.div
            key="complete"
            className="px-6 md:px-12 py-12 space-y-16"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {/* Timeline */}
            <InvestigationTimeline
              steps={steps}
              investigationId={investigationId}
            />

            {/* Match */}
            {traceResult.result.best_match && (
              <MatchComparison
                inputImage={imagePreview}
                match={traceResult.result.best_match}
              />
            )}

            {/* Fingerprint */}
            <FingerprintDisplay
              hash={traceResult.result.fingerprint.content_hash}
              imageSha256={traceResult.result.fingerprint.image_sha256}
            />

            {/* Blockchain Proof */}
            {traceResult.result.blockchain && (
              <BlockchainProof
                txHash={traceResult.result.blockchain.tx_hash}
                blockNumber={traceResult.result.blockchain.block_number}
                network={traceResult.result.blockchain.network}
                chainId={traceResult.result.blockchain.chain_id}
                contractAddress={traceResult.result.blockchain.contract_address}
                timestamp={traceResult.result.blockchain.timestamp}
                gasUsed={traceResult.result.blockchain.gas_used}
              />
            )}

            {/* Verification */}
            {traceResult.result.verification && traceResult.result.blockchain && (
              <VerificationResult
                localHash={traceResult.result.fingerprint.content_hash}
                onChainHash={traceResult.result.fingerprint.content_hash}
                verified={traceResult.result.verification.exists}
                network={traceResult.result.blockchain.network}
                timestamp={traceResult.result.verification.timestamp}
              />
            )}

            {/* Tamper Check */}
            <TamperCheck contentHash={traceResult.result.fingerprint.content_hash} />

            {/* New Trace */}
            <div className="max-w-3xl mx-auto text-center pt-8 border-t border-trace-yellow/20">
              <button
                onClick={handleReset}
                className="px-8 py-4 bg-trace-yellow text-trace-ink font-display font-bold text-lg border-4 border-trace-ink hover:bg-trace-pink hover:text-white transition-colors"
              >
                NEW TRACE →
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="px-6 md:px-12 py-6 border-t border-trace-yellow/10 mt-12">
        <div className="flex justify-between items-center">
          <span className="font-mono text-xs text-trace-yellow/30">
            TRACE v1.0 · HH Goa 2026
          </span>
          <span className="font-mono text-xs text-trace-yellow/30">
            चेहरा → सबूत
          </span>
        </div>
      </footer>
    </main>
  );
}

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
  const [resetKey, setResetKey] = useState<number>(0);
  const [investigationId, setInvestigationId] = useState<string>(() =>
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

  const handleFileSelect = useCallback((f: File) => {
    setFile(f);
    setImagePreview(URL.createObjectURL(f));
  }, []);

  const deriveTimelineSteps = useCallback(
    (result: TraceResult | null, fallbackError?: string): TimelineStep[] => {
      const baseSteps: TimelineStep[] = [
        { id: "face", label: "Face Analysis", status: "queued" },
        { id: "search", label: "Web Discovery", status: "queued" },
        { id: "match", label: "Candidate Matching", status: "queued" },
        { id: "fingerprint", label: "Content Fingerprint", status: "queued" },
        { id: "proof", label: "Blockchain Proof", status: "queued" },
        { id: "verify", label: "Verification", status: "queued" },
      ];

      if (!result) return baseSteps;

      const serverSteps = result.steps || [];
      const serverStepMap = new Map<string, (typeof serverSteps)[number]>();
      serverSteps.forEach((s) => serverStepMap.set(s.step, s));

      const stepKeys = [
        { id: "face", serverName: "face_analysis" },
        { id: "search", serverName: "web_search" },
        { id: "match", serverName: "candidate_matching" },
        { id: "fingerprint", serverName: "fingerprint" },
        { id: "proof", serverName: "blockchain_registration" },
        { id: "verify", serverName: "verification" },
      ];

      let hasFailed = false;

      return stepKeys.map(({ id, serverName }, index) => {
        const defaultLabel = baseSteps[index].label;

        if (hasFailed) {
          return {
            id,
            label: defaultLabel,
            status: "skipped",
            detail: "Skipped",
          };
        }

        const s = serverStepMap.get(serverName);

        if (!s) {
          return {
            id,
            label: defaultLabel,
            status: "skipped",
            detail: "Not executed",
          };
        }

        if (
          s.status === "failed" ||
          s.status === "no_results" ||
          s.status === "no_match"
        ) {
          hasFailed = true;
          let detail =
            (s.error as string | undefined) ||
            result.error ||
            fallbackError ||
            "Failed";
          if (id === "face") {
            detail = (s.error as string | undefined) || "No detectable face in image";
          } else if (id === "search") {
            detail = result.error || "No visual occurrences indexed on web";
          } else if (id === "match") {
            detail = result.error || "No candidate matched face embedding";
          } else if (id === "proof") {
            detail = (s.error as string | undefined) || "Blockchain transaction failed";
          }
          return {
            id,
            label: defaultLabel,
            status: "failed",
            detail,
          };
        }

        if (s.status === "skipped") {
          return {
            id,
            label: defaultLabel,
            status: "skipped",
            detail: (s.reason as string | undefined) || "Skipped",
          };
        }

        if (s.status === "complete" || s.status === "verified") {
          let detail = "Completed";
          if (id === "face") {
            const fc =
              (s.face_count as number | undefined) ||
              result.result?.face_analysis?.face_count ||
              1;
            const conf =
              s.confidence !== undefined
                ? (Number(s.confidence) * 100).toFixed(0)
                : result.result?.face_analysis
                ? (result.result.face_analysis.confidence * 100).toFixed(0)
                : "100";
            detail = `${fc} face(s) · ${conf}% confidence`;
          } else if (id === "search") {
            const cCount =
              (s.candidates_found as number | undefined) !== undefined
                ? (s.candidates_found as number)
                : result.result?.all_matches?.length || 0;
            const prov =
              (s.provider as string | undefined) ||
              result.result?.search_provider ||
              "Google Lens";
            detail = `${cCount} candidates via ${prov}`;
          } else if (id === "match") {
            const sim = result.result?.best_match
              ? (result.result.best_match.similarity_score * 100).toFixed(1)
              : s.best_similarity !== undefined
              ? (Number(s.best_similarity) * 100).toFixed(1)
              : "100";
            detail = `Top match: ${sim}% similarity`;
          } else if (id === "fingerprint") {
            const hash =
              (s.content_hash as string | undefined) ||
              result.result?.fingerprint?.content_hash ||
              "";
            detail = hash
              ? `SHA-256: ${hash.slice(0, 16)}...`
              : "SHA-256 computed";
          } else if (id === "proof") {
            const block =
              (s.block_number as number | undefined) ||
              result.result?.blockchain?.block_number;
            const net =
              (s.network as string | undefined) ||
              result.result?.blockchain?.network ||
              "EVM";
            detail = block ? `Block #${block} · ${net}` : "Evidence notarized";
          } else if (id === "verify") {
            detail = result.result?.verification?.exists
              ? "Content integrity confirmed"
              : "On-chain proof verified";
          }

          return {
            id,
            label: defaultLabel,
            status: "complete",
            detail,
          };
        }

        return {
          id,
          label: defaultLabel,
          status: "failed",
          detail: "Unexpected status",
        };
      });
    },
    []
  );

  const handleBeginTrace = useCallback(async () => {
    if (!file) return;

    setPhase("investigating");
    setError("");

    setSteps([
      {
        id: "face",
        label: "Face Analysis",
        status: "scanning",
        detail: "Detecting facial geometry & 512-d embedding...",
      },
      { id: "search", label: "Web Discovery", status: "queued" },
      { id: "match", label: "Candidate Matching", status: "queued" },
      { id: "fingerprint", label: "Content Fingerprint", status: "queued" },
      { id: "proof", label: "Blockchain Proof", status: "queued" },
      { id: "verify", label: "Verification", status: "queued" },
    ]);

    const searchTimer = setTimeout(() => {
      setSteps((prev) =>
        prev.map((s) => {
          if (s.id === "face")
            return {
              ...s,
              status: "complete",
              detail: "Face detected & embedding extracted",
            };
          if (s.id === "search")
            return {
              ...s,
              status: "scanning",
              detail: "Searching Google Lens with SafeSearch...",
            };
          return s;
        })
      );
    }, 800);

    try {
      const result = await runFullTrace(file);
      clearTimeout(searchTimer);

      const finalSteps = deriveTimelineSteps(result);
      setSteps(finalSteps);
      setTraceResult(result);

      if (result.success && result.result) {
        setPhase("complete");
      } else {
        setError(result.error || "Investigation did not complete successfully");
        setPhase("error");
      }
    } catch (e) {
      clearTimeout(searchTimer);
      const msg =
        e instanceof Error ? e.message : "An unexpected error occurred";
      setError(msg);
      setSteps((prev) =>
        prev.map((s) => {
          if (s.status === "scanning")
            return { ...s, status: "failed", detail: msg };
          if (s.status === "queued")
            return { ...s, status: "skipped", detail: "Skipped" };
          return s;
        })
      );
      setPhase("error");
    }
  }, [file, deriveTimelineSteps]);

  const handleReset = useCallback(() => {
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }
    setPhase("landing");
    setFile(null);
    setImagePreview("");
    setTraceResult(null);
    setError("");
    setResetKey((k) => k + 1);
    setInvestigationId(Math.random().toString(36).slice(2, 8).toUpperCase());
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
    <main
      className={`bg-trace-green text-trace-yellow transition-all ${
        phase === "landing"
          ? "h-screen max-h-screen overflow-hidden flex flex-col justify-between"
          : "min-h-screen flex flex-col justify-between"
      }`}
    >
      {/* Navigation Header */}
      <nav className="flex items-center justify-between px-6 md:px-12 py-3.5 border-b border-trace-yellow/15 flex-shrink-0">
        <div className="cursor-pointer" onClick={handleReset}>
          <TraceLogo size="small" />
        </div>
        <div className="flex items-center gap-4 sm:gap-6">
          <span className="hidden sm:inline-block font-mono text-[11px] text-trace-cream/60 bg-trace-ink px-2.5 py-1 border border-trace-yellow/20">
            EVM NOTARIZED
          </span>
          <span className="font-mono text-xs text-trace-yellow/70 uppercase tracking-wider font-bold">
            HH GOA 2026
          </span>
        </div>
      </nav>

      {/* Dynamic Content */}
      <AnimatePresence mode="wait">
        {/* === LANDING VIEW (FITS 100% IN VIEWPORT, ZERO SCROLL) === */}
        {phase === "landing" && (
          <motion.div
            key="landing"
            className="flex-1 flex items-center px-6 md:px-12 py-4 max-w-7xl mx-auto w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center w-full">
              {/* Left Column: Poster Identity */}
              <div className="lg:col-span-7 space-y-4">
                <TraceLogo size="large" />

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-4 border-t border-trace-yellow/20 max-w-xl">
                  <div className="bg-trace-ink p-2.5 border border-trace-yellow/30 shadow-[3px_3px_0px_#082F1C]">
                    <span className="font-mono text-[9px] text-trace-pink font-bold block">01. DISCOVER</span>
                    <span className="font-mono text-xs text-trace-cream font-bold">Reverse Web Search</span>
                  </div>
                  <div className="bg-trace-ink p-2.5 border border-trace-yellow/30 shadow-[3px_3px_0px_#082F1C]">
                    <span className="font-mono text-[9px] text-trace-pink font-bold block">02. VERIFY</span>
                    <span className="font-mono text-xs text-trace-cream font-bold">ArcFace 512-d Match</span>
                  </div>
                  <div className="bg-trace-ink p-2.5 border border-trace-yellow/30 shadow-[3px_3px_0px_#082F1C]">
                    <span className="font-mono text-[9px] text-trace-pink font-bold block">03. PROVE</span>
                    <span className="font-mono text-xs text-trace-cream font-bold">On-Chain SHA-256</span>
                  </div>
                </div>
              </div>

              {/* Right Column: Upload Card */}
              <div className="lg:col-span-5 flex justify-center lg:justify-end">
                <UploadZone
                  key={resetKey}
                  onFileSelect={handleFileSelect}
                  onBeginTrace={handleBeginTrace}
                  disabled={phase !== "landing"}
                />
              </div>
            </div>
          </motion.div>
        )}

        {/* === INVESTIGATING & ERROR VIEW === */}
        {(phase === "investigating" || phase === "error") && (
          <motion.div
            key="investigating"
            className="flex-1 px-6 md:px-12 py-10 max-w-4xl mx-auto w-full flex flex-col justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <InvestigationTimeline steps={steps} investigationId={investigationId} />

            {phase === "error" && error && (
              <motion.div
                className="max-w-3xl mx-auto mt-6 p-6 bg-trace-ink border-3 border-trace-pink shadow-[8px_8px_0px_#082F1C]"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-2.5 h-2.5 bg-trace-pink rounded-full inline-block animate-ping" />
                  <span className="font-mono text-[11px] font-bold text-trace-pink uppercase tracking-widest">
                    INVESTIGATION STATUS
                  </span>
                </div>
                <h3 className="font-display font-black text-xl text-trace-yellow mb-2 uppercase">
                  {error.includes("safety") || error.includes("NSFW") || error.includes("adult")
                    ? "DISCOVERED OCCURRENCES BLOCKED BY SAFETY POLICY"
                    : error.includes("indexed")
                    ? "ZERO PUBLIC OCCURRENCES INDEXED"
                    : "INVESTIGATION NOT COMPLETED"}
                </h3>
                <p className="font-mono text-xs text-trace-cream/90 leading-relaxed bg-trace-green/40 p-3 border border-trace-yellow/20">
                  {error}
                </p>
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={handleReset}
                    className="px-6 py-2.5 bg-trace-yellow text-trace-ink font-mono font-black text-xs uppercase border-3 border-trace-ink shadow-[3px_3px_0px_#082F1C] hover:bg-trace-pink hover:text-white transition-all cursor-pointer"
                  >
                    ← TRY ANOTHER IMAGE
                  </button>
                </div>
              </motion.div>
            )}
          </motion.div>
        )}

        {/* === COMPLETE VIEW === */}
        {phase === "complete" && traceResult?.result && (
          <motion.div
            key="complete"
            className="flex-1 px-6 md:px-12 py-10 space-y-12 max-w-5xl mx-auto w-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <InvestigationTimeline steps={steps} investigationId={investigationId} />

            {traceResult.result.best_match && (
              <MatchComparison inputImage={imagePreview} match={traceResult.result.best_match} />
            )}

            <FingerprintDisplay
              hash={traceResult.result.fingerprint.content_hash}
              imageSha256={traceResult.result.fingerprint.image_sha256}
            />

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

            {traceResult.result.verification && traceResult.result.blockchain && (
              <VerificationResult
                localHash={traceResult.result.fingerprint.content_hash}
                onChainHash={traceResult.result.fingerprint.content_hash}
                verified={traceResult.result.verification.exists}
                network={traceResult.result.blockchain.network}
                timestamp={traceResult.result.verification.timestamp}
              />
            )}

            <TamperCheck contentHash={traceResult.result.fingerprint.content_hash} />

            <div className="text-center pt-6 border-t border-trace-yellow/20">
              <button
                type="button"
                onClick={handleReset}
                className="px-8 py-3.5 bg-trace-yellow text-trace-ink font-display font-black text-lg uppercase border-3 border-trace-ink shadow-[5px_5px_0px_#082F1C] hover:bg-trace-pink hover:text-white transition-all cursor-pointer"
              >
                NEW INVESTIGATION →
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer Bar */}
      <footer className="px-6 md:px-12 py-3 border-t border-trace-yellow/15 flex-shrink-0">
        <div className="flex justify-between items-center max-w-7xl mx-auto w-full">
          <span className="font-mono text-[11px] text-trace-yellow/40 uppercase">
            TRACE v1.0 · HH Goa 2026
          </span>
          <span className="font-mono text-[11px] text-trace-yellow/40">
            चेहरा → सबूत · DISCOVER · VERIFY · PROVE
          </span>
        </div>
      </footer>
    </main>
  );
}

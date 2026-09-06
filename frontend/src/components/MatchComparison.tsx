"use client";

import { motion } from "framer-motion";
import type { SearchMatch } from "@/lib/api";

interface MatchComparisonProps {
  inputImage: string;
  match: SearchMatch;
}

export default function MatchComparison({ inputImage, match }: MatchComparisonProps) {
  const similarityPct = (match.similarity_score * 100).toFixed(1);

  return (
    <motion.div
      className="w-full max-w-4xl mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="flex items-center justify-between border-b-3 border-trace-yellow pb-3 mb-8">
        <h2 className="font-display font-black text-2xl sm:text-4xl text-trace-yellow uppercase tracking-tight">
          VISUAL EVIDENCE MATCH
        </h2>
        {match.is_social && (
          <span className="bg-trace-pink text-white font-mono font-bold text-xs px-3 py-1 uppercase tracking-wider border border-trace-ink shadow-[2px_2px_0px_#082F1C]">
            SOCIAL MEDIA
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
        {/* Input Image */}
        <div className="space-y-2">
          <div className="bg-trace-ink text-trace-yellow px-3 py-1 font-mono font-bold text-xs uppercase tracking-widest border border-trace-yellow/40">
            01. INPUT TARGET
          </div>
          <div className="border-3 border-trace-yellow p-1 bg-trace-ink shadow-[4px_4px_0px_#082F1C]">
            <img src={inputImage} alt="Input Target" className="w-full h-64 object-cover" />
          </div>
        </div>

        {/* Similarity Score Center Block */}
        <div className="flex flex-col items-center justify-center p-6 bg-trace-ink border-3 border-trace-yellow shadow-[6px_6px_0px_#082F1C]">
          <span className="font-mono text-xs text-trace-pink font-bold uppercase tracking-widest mb-1">
            FACIAL SIMILARITY
          </span>
          <motion.div
            className="font-display font-black text-6xl sm:text-7xl text-trace-yellow leading-none my-2"
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 200 }}
          >
            {similarityPct}%
          </motion.div>
          <span className="font-mono text-[11px] text-trace-cream/70 uppercase tracking-widest">
            COSINE DISTANCE: {match.similarity_score.toFixed(4)}
          </span>

          <div className="mt-6 w-full pt-4 border-t border-trace-yellow/20 space-y-2">
            <div className="flex items-center gap-2">
              <span className="annotation-dot" />
              <span className="font-mono text-xs text-trace-cream">FACE DETECTED</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="annotation-dot" />
              <span className="font-mono text-xs text-trace-cream">ARC-FACE EMBEDDING</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="annotation-dot" />
              <span className="font-mono text-xs text-trace-cream">SOURCE VERIFIED</span>
            </div>
          </div>
        </div>

        {/* Discovered Source */}
        <div className="space-y-2">
          <div className="bg-trace-ink text-trace-pink px-3 py-1 font-mono font-bold text-xs uppercase tracking-widest border border-trace-pink/40">
            02. DISCOVERED SOURCE
          </div>
          <div className="border-3 border-trace-pink p-1 bg-trace-ink shadow-[4px_4px_0px_#082F1C]">
            {match.image_url ? (
              <img
                src={match.image_url}
                alt="Discovered Source"
                className="w-full h-64 object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = match.thumbnail_url || "";
                }}
              />
            ) : (
              <div className="h-64 flex items-center justify-center bg-trace-ink/80 text-trace-cream/50 font-mono text-xs">
                IMAGE PREVIEW UNAVAILABLE
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Source Details Evidence Block */}
      <div className="evidence-block mt-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <span className="font-mono text-[10px] text-trace-ink/60 font-bold uppercase tracking-wider">
              SOURCE DOMAIN
            </span>
            <p className="font-mono text-base font-black text-trace-ink mt-0.5">
              {match.domain || "Web Source"}
            </p>
          </div>
          <div>
            <span className="font-mono text-[10px] text-trace-ink/60 font-bold uppercase tracking-wider">
              PAGE TITLE
            </span>
            <p className="font-mono text-sm font-bold text-trace-ink line-clamp-2 mt-0.5">
              {match.page_title || "Untitled Web Resource"}
            </p>
          </div>
          <div className="md:col-span-2 pt-2 border-t border-trace-ink/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="overflow-hidden">
              <span className="font-mono text-[10px] text-trace-ink/60 font-bold uppercase tracking-wider block">
                CANONICAL SOURCE URL
              </span>
              <p className="font-mono text-xs text-trace-ink truncate max-w-xl">
                {match.source_url}
              </p>
            </div>
            <a
              href={match.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-trace-ink text-trace-yellow font-mono font-bold text-xs uppercase border-2 border-trace-ink hover:bg-trace-pink hover:text-white transition-colors flex-shrink-0 shadow-[2px_2px_0px_#05472A]"
            >
              VIEW SOURCE ↗
            </a>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

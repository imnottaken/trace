"use client";

import { motion } from "framer-motion";
import type { SearchMatch } from "@/lib/api";

interface MatchComparisonProps {
  inputImage: string; // Object URL or data URL
  match: SearchMatch;
}

export default function MatchComparison({ inputImage, match }: MatchComparisonProps) {
  const similarityPct = (match.similarity_score * 100).toFixed(1);

  return (
    <motion.div
      className="w-full max-w-4xl mx-auto"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <h2 className="font-display font-bold text-3xl text-trace-yellow mb-6 border-b-2 border-trace-yellow/30 pb-3">
        MATCH RESULT
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        {/* Input Image */}
        <div className="space-y-2">
          <span className="font-mono text-xs text-trace-yellow/60 uppercase tracking-widest">
            INPUT
          </span>
          <div className="border-2 border-trace-yellow p-1">
            <img src={inputImage} alt="Input" className="w-full object-cover" />
          </div>
        </div>

        {/* Similarity Score */}
        <div className="flex flex-col items-center justify-center py-8">
          <span className="font-mono text-xs text-trace-pink uppercase tracking-widest mb-2">
            FACE MATCH
          </span>
          <motion.div
            className="font-display font-black text-6xl text-trace-yellow"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", delay: 0.3 }}
          >
            {similarityPct}%
          </motion.div>
          <span className="font-mono text-xs text-trace-cream/60 mt-2">
            VISUAL SIMILARITY
          </span>

          <div className="mt-6 space-y-2">
            <div className="flex items-center gap-2">
              <span className="annotation-dot" />
              <span className="font-mono text-xs text-trace-cream">SAME FACE</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="annotation-dot" />
              <span className="font-mono text-xs text-trace-cream">
                {match.is_social ? "SOCIAL MEDIA MATCH" : "SOURCE FOUND"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="annotation-dot" />
              <span className="font-mono text-xs text-trace-cream">MATCH VERIFIED</span>
            </div>
          </div>
        </div>

        {/* Discovered Source */}
        <div className="space-y-2">
          <span className="font-mono text-xs text-trace-yellow/60 uppercase tracking-widest">
            DISCOVERED SOURCE
          </span>
          <div className="border-2 border-trace-pink p-1">
            {match.image_url ? (
              <img
                src={match.image_url}
                alt="Discovered"
                className="w-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).src =
                    match.thumbnail_url || "";
                }}
              />
            ) : (
              <div className="h-48 flex items-center justify-center bg-trace-ink/50">
                <span className="font-mono text-xs text-trace-cream/40">
                  IMAGE NOT AVAILABLE
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Source Details */}
      <div className="evidence-block mt-8">
        <div className="space-y-3">
          <div>
            <span className="font-mono text-xs text-trace-ink/60 uppercase">SOURCE FOUND</span>
            <p className="font-mono text-sm font-bold">{match.domain || "Unknown"}</p>
          </div>
          <div>
            <span className="font-mono text-xs text-trace-ink/60 uppercase">SOURCE URL</span>
            <p className="font-mono text-xs break-all">{match.source_url}</p>
          </div>
          {match.page_title && (
            <div>
              <span className="font-mono text-xs text-trace-ink/60 uppercase">TITLE</span>
              <p className="font-mono text-sm">{match.page_title}</p>
            </div>
          )}
          <a
            href={match.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block mt-2 font-mono text-sm font-bold text-trace-pink underline hover:text-trace-ink"
          >
            VIEW SOURCE ↗
          </a>
        </div>
      </div>
    </motion.div>
  );
}

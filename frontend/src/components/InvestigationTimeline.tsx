"use client";

import { motion } from "framer-motion";

export type StepStatus = "queued" | "scanning" | "complete" | "failed" | "skipped";

export interface TimelineStep {
  id: string;
  label: string;
  status: StepStatus;
  detail?: string;
}

interface InvestigationTimelineProps {
  steps: TimelineStep[];
  investigationId?: string;
}

const statusConfig: Record<StepStatus, { badge: string; badgeBg: string; textColor: string }> = {
  queued: { badge: "QUEUED", badgeBg: "bg-trace-ink text-trace-yellow/40 border-trace-yellow/20", textColor: "text-trace-yellow/40" },
  scanning: { badge: "SCANNING...", badgeBg: "bg-trace-yellow text-trace-ink animate-pulse", textColor: "text-trace-yellow" },
  complete: { badge: "COMPLETE ✓", badgeBg: "bg-green-400 text-trace-ink font-bold", textColor: "text-green-400" },
  failed: { badge: "FAILED ✗", badgeBg: "bg-trace-pink text-white font-bold", textColor: "text-trace-pink" },
  skipped: { badge: "SKIPPED", badgeBg: "bg-trace-ink text-trace-yellow/20 border-trace-yellow/10", textColor: "text-trace-yellow/30" },
};

export default function InvestigationTimeline({
  steps,
  investigationId,
}: InvestigationTimelineProps) {
  return (
    <div className="w-full max-w-3xl mx-auto bg-trace-ink p-6 sm:p-8 border-3 border-trace-yellow shadow-[8px_8px_0px_#082F1C]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between border-b-2 border-trace-yellow/30 pb-4 mb-6 gap-2">
        <h2 className="font-display font-black text-xl sm:text-2xl text-trace-yellow uppercase tracking-tight">
          INVESTIGATION PIPELINE
        </h2>
        {investigationId && (
          <span className="font-mono text-xs text-trace-cream/70 bg-trace-green px-2.5 py-1 border border-trace-yellow/30">
            CASE #{investigationId}
          </span>
        )}
      </div>

      {/* Steps */}
      <div className="space-y-4">
        {steps.map((step, i) => {
          const config = statusConfig[step.status];
          return (
            <motion.div
              key={step.id}
              className="flex items-start justify-between gap-4 p-3 bg-trace-green/40 border border-trace-yellow/20"
              initial={{ opacity: 0, x: -15 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs font-bold text-trace-pink">
                  0{i + 1}.
                </span>
                <div>
                  <p className="font-mono text-sm font-bold uppercase text-trace-yellow">
                    {step.label}
                  </p>
                  {step.detail && (
                    <p className="font-mono text-xs text-trace-cream/80 mt-0.5">
                      {step.detail}
                    </p>
                  )}
                </div>
              </div>

              <span
                className={`font-mono text-[10px] uppercase px-2.5 py-1 border border-trace-ink shadow-[2px_2px_0px_#082F1C] ${config.badgeBg}`}
              >
                {config.badge}
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

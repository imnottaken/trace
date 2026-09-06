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

const statusConfig: Record<StepStatus, { icon: string; color: string; glow: boolean }> = {
  queued: { icon: "○", color: "text-trace-yellow/30", glow: false },
  scanning: { icon: "◉", color: "text-trace-yellow", glow: true },
  complete: { icon: "✓", color: "text-green-400", glow: false },
  failed: { icon: "✗", color: "text-trace-pink", glow: false },
  skipped: { icon: "—", color: "text-trace-yellow/20", glow: false },
};

export default function InvestigationTimeline({
  steps,
  investigationId,
}: InvestigationTimelineProps) {
  return (
    <div className="w-full max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-8 border-b-2 border-trace-yellow/30 pb-3">
        <h2 className="font-display font-bold text-2xl text-trace-yellow">
          TRACE
        </h2>
        {investigationId && (
          <span className="font-mono text-xs text-trace-cream/60">
            INVESTIGATION #{investigationId}
          </span>
        )}
      </div>

      {/* Steps */}
      <div className="space-y-1">
        {steps.map((step, i) => {
          const config = statusConfig[step.status];
          return (
            <motion.div
              key={step.id}
              className="flex items-start gap-4 py-3"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              {/* Status Icon */}
              <div className="flex flex-col items-center min-w-[32px]">
                <motion.span
                  className={`text-xl font-mono ${config.color} ${
                    config.glow ? "animate-pulse" : ""
                  }`}
                  animate={config.glow ? { opacity: [0.5, 1, 0.5] } : {}}
                  transition={
                    config.glow
                      ? { repeat: Infinity, duration: 1.5 }
                      : {}
                  }
                >
                  {config.icon}
                </motion.span>
                {i < steps.length - 1 && (
                  <div
                    className={`w-px h-6 mt-1 ${
                      step.status === "complete"
                        ? "bg-green-400/50"
                        : "bg-trace-yellow/10"
                    }`}
                  />
                )}
              </div>

              {/* Content */}
              <div className="flex-1">
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-sm font-bold uppercase tracking-wider text-trace-yellow">
                    {step.label}
                  </span>
                  <span
                    className={`font-mono text-xs uppercase tracking-widest ${config.color}`}
                  >
                    {step.status === "scanning" ? "SCANNING..." : step.status.toUpperCase()}
                  </span>
                </div>
                {step.detail && (
                  <p className="font-mono text-xs text-trace-cream/70 mt-1">
                    {step.detail}
                  </p>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

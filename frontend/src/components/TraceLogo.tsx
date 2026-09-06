"use client";

export default function TraceLogo({ size = "large" }: { size?: "large" | "small" }) {
  if (size === "small") {
    return (
      <div className="select-none flex items-baseline gap-3">
        <h1 className="font-display font-black text-3xl text-trace-yellow tracking-tighter">
          TRACE
        </h1>
        <span className="font-devanagari text-base text-trace-cream/80">
          चेहरा → सबूत
        </span>
      </div>
    );
  }

  return (
    <div className="select-none">
      <div className="inline-block bg-trace-yellow text-trace-ink font-mono font-bold text-xs px-3 py-1 mb-4 uppercase tracking-widest border border-trace-ink shadow-[3px_3px_0px_#082F1C]">
        HH GOA 2026 · INVESTIGATION PROTOCOL
      </div>
      <h1 className="font-display font-black text-6xl sm:text-8xl md:text-9xl lg:text-[10rem] text-trace-yellow leading-[0.85] tracking-tighter uppercase drop-shadow-[4px_4px_0px_#082F1C]">
        TRACE
      </h1>
      <p className="font-devanagari text-2xl sm:text-4xl text-trace-cream mt-3 font-normal">
        चेहरा → सबूत
      </p>
      <div className="flex items-center gap-3 mt-4">
        <span className="h-0.5 w-8 bg-trace-pink inline-block" />
        <p className="font-mono text-xs sm:text-sm text-trace-yellow font-bold tracking-[0.3em] uppercase">
          Discover · Verify · Prove
        </p>
      </div>
    </div>
  );
}

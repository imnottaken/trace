"use client";

export default function TraceLogo({ size = "large" }: { size?: "large" | "small" }) {
  if (size === "small") {
    return (
      <div className="select-none">
        <h1 className="font-display font-black text-3xl text-trace-yellow tracking-tight">
          TRACE
        </h1>
      </div>
    );
  }

  return (
    <div className="select-none">
      <h1 className="font-display font-black text-hero text-trace-yellow leading-none tracking-tighter">
        TRACE
      </h1>
      <p className="font-devanagari text-hero-sub text-trace-cream mt-2">
        चेहरा → सबूत
      </p>
      <p className="font-mono text-sm md:text-base text-trace-yellow/70 tracking-[0.3em] uppercase mt-4">
        Discover · Verify · Prove
      </p>
    </div>
  );
}

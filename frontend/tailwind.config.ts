import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        trace: {
          green: "#05472A",
          "green-light": "#006B3C",
          yellow: "#F7E000",
          pink: "#FF0A87",
          ink: "#082F1C",
          cream: "#F5E7A1",
          white: "#FAFAF5",
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', "Georgia", "serif"],
        mono: ['"JetBrains Mono"', "monospace"],
        devanagari: ['"Tiro Devanagari Hindi"', "serif"],
      },
      fontSize: {
        "hero": ["clamp(4rem, 12vw, 14rem)", { lineHeight: "0.9", letterSpacing: "-0.03em" }],
        "hero-sub": ["clamp(1.2rem, 3vw, 2.5rem)", { lineHeight: "1.2" }],
      },
    },
  },
  plugins: [],
};
export default config;

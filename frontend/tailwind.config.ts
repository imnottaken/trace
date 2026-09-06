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
        display: ["var(--font-playfair)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "monospace"],
        devanagari: ["var(--font-devanagari)", "serif"],
      },
    },
  },
  plugins: [],
};
export default config;

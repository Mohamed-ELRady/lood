import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "var(--ink)",
        paper: "var(--paper)",
        panel: "var(--panel)",
        line: "var(--line)",
        signal: "var(--signal)",
        coral: "var(--coral)",
        muted: "var(--muted)"
      },
      fontFamily: {
        body: ["IBM Plex Sans Arabic", "Noto Sans Arabic", "Segoe UI", "sans-serif"],
        display: ["Arial Rounded MT Bold", "Avenir Next", "Noto Sans Arabic", "sans-serif"],
        mono: ["SFMono-Regular", "Consolas", "monospace"]
      },
      boxShadow: {
        float: "0 24px 70px rgba(25, 44, 120, 0.13)",
        signal: "0 12px 36px rgba(66, 91, 255, 0.28)"
      }
    }
  },
  plugins: []
};

export default config;


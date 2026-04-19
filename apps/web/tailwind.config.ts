import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "rgb(var(--background) / <alpha-value>)",
        panel: "rgb(var(--panel) / <alpha-value>)",
        "panel-strong": "rgb(var(--panel-strong) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        foreground: "rgb(var(--foreground) / <alpha-value>)",
        "muted-foreground": "rgb(var(--muted-foreground) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        "accent-foreground": "rgb(var(--accent-foreground) / <alpha-value>)",
        success: "rgb(var(--success) / <alpha-value>)",
        danger: "rgb(var(--danger) / <alpha-value>)",
        "signal-cyan": "rgb(var(--signal-cyan) / <alpha-value>)",
      },
      boxShadow: {
        panel: "0 24px 80px rgba(15, 23, 42, 0.08)",
        "panel-dark": "0 20px 80px rgba(0, 255, 65, 0.12)",
      },
      fontFamily: {
        headline: ["var(--font-space-grotesk)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      backgroundImage: {
        vellum:
          "linear-gradient(90deg, rgba(var(--line), 0.18) 1px, transparent 1px), linear-gradient(rgba(var(--line), 0.18) 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;

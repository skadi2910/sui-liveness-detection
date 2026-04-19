"use client";

import { useTheme } from "./theme-provider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      aria-label="Toggle light and dark theme"
      className="inline-flex h-10 items-center gap-2 border border-line bg-panel px-3 text-[0.68rem] uppercase tracking-[0.24em] text-muted-foreground transition hover:border-accent hover:text-foreground"
      onClick={toggleTheme}
      type="button"
    >
      <span className="inline-flex h-2 w-2 rounded-full bg-accent" />
      {theme === "light" ? "Dark mode" : "Light mode"}
    </button>
  );
}

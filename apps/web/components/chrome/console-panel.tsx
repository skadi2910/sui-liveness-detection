import type { ReactNode } from "react";

type PanelAccent = "accent" | "signal" | "neutral";

function accentClassName(accent: PanelAccent) {
  if (accent === "signal") return "bg-signal-cyan/70";
  if (accent === "neutral") return "bg-line/70";
  return "bg-accent/70";
}

export function ConsolePanel(props: {
  accent?: PanelAccent;
  children: ReactNode;
  className?: string;
  description?: string;
  eyebrow?: string;
  title?: string;
}) {
  return (
    <section
      className={`relative overflow-hidden border border-line/70 bg-panel/90 p-6 shadow-panel ${
        props.className ?? ""
      }`}
    >
      <div className={`absolute inset-x-0 top-0 h-px ${accentClassName(props.accent ?? "accent")}`} />
      {props.eyebrow || props.title || props.description ? (
        <div className="mb-5 grid gap-2">
          {props.eyebrow ? (
            <p className="text-[0.65rem] uppercase tracking-[0.28em] text-accent">{props.eyebrow}</p>
          ) : null}
          {props.title ? (
            <h2 className="font-headline text-2xl font-black uppercase tracking-tight text-foreground">
              {props.title}
            </h2>
          ) : null}
          {props.description ? (
            <p className="max-w-2xl text-sm leading-7 text-muted-foreground">{props.description}</p>
          ) : null}
        </div>
      ) : null}
      {props.children}
    </section>
  );
}

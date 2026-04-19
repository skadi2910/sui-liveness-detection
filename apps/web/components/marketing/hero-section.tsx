import Link from "next/link";
import { LaunchVerificationButton } from "@/components/verification/launch-verification-button";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden border-b border-line/70">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(0,85,255,0.18),transparent_40%),linear-gradient(180deg,transparent,rgba(0,0,0,0.03))]" />
      <div className="absolute inset-y-0 right-[12%] hidden w-px bg-line/50 lg:block" />
      <div className="absolute inset-y-0 right-[24%] hidden w-px bg-line/30 lg:block" />

      <div className="relative mx-auto grid min-h-[calc(100svh-72px)] max-w-7xl gap-12 px-4 py-12 sm:px-6 lg:grid-cols-[minmax(0,1.1fr)_26rem] lg:items-center lg:py-16">
        <div className="flex max-w-3xl flex-col justify-center">
          <p className="mb-4 text-[0.68rem] uppercase tracking-[0.34em] text-accent">
            Identity attestation / protocol v2
          </p>
          <h1 className="font-headline text-[clamp(3.3rem,11vw,8.5rem)] font-black uppercase leading-[0.9] tracking-[-0.06em] text-foreground">
            Sovereign
            <br />
            <span className="text-accent">Humanity</span>
          </h1>
          <p className="mt-6 max-w-xl border-l-2 border-accent pl-5 text-sm leading-7 text-muted-foreground sm:text-base">
            Sui Human anchors digital access in real biological presence with a
            verification flow built for liveness, anti-spoofing, and privacy-first
            trust.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <LaunchVerificationButton label="Launch app" />
            <Link
              className="inline-flex items-center justify-center border border-line bg-panel px-5 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-foreground transition hover:border-accent hover:text-accent"
              href="/overview"
            >
              Read overview
            </Link>
          </div>
          <div className="mt-5 flex flex-wrap gap-3 text-[0.64rem] uppercase tracking-[0.24em] text-muted-foreground">
            <Link className="transition hover:text-accent" href="/about">
              Mission profile
            </Link>
            <span className="text-line">/</span>
            <Link className="transition hover:text-accent" href="/app">
              Main app shell
            </Link>
          </div>
        </div>

        <div className="grid gap-4 border border-line/70 bg-panel p-4 shadow-panel sm:p-6">
          <div className="grid grid-cols-[1fr_auto] gap-4 border-b border-line/60 pb-4">
            <div>
              <p className="text-[0.66rem] uppercase tracking-[0.28em] text-muted-foreground">
                Session posture
              </p>
              <h2 className="mt-2 font-headline text-2xl font-bold uppercase tracking-tight text-foreground">
                Ready to verify
              </h2>
            </div>
            <div className="text-right text-[0.62rem] uppercase tracking-[0.24em] text-signal-cyan">
              Live / wallet-ready
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ["Biometric hash", "Frame-derived identity signals are evaluated before any downstream proof step."],
              ["Liveness check", "Challenge-response motion makes replay and static attacks harder to pass."],
              ["Neural validation", "Passive anti-spoof scoring runs in the same session without exposing operator telemetry."],
              ["Result handoff", "Verified, failed, spoof-oriented, and expired outcomes route cleanly to the client result view."],
            ].map(([title, body]) => (
              <article
                className="border border-line/60 bg-background/70 p-4 transition hover:border-accent/70"
                key={title}
              >
                <p className="text-[0.62rem] uppercase tracking-[0.3em] text-muted-foreground">
                  Capability
                </p>
                <h3 className="mt-3 font-headline text-lg font-bold uppercase tracking-tight text-foreground">
                  {title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

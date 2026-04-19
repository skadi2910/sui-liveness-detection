import Link from "next/link";
import { LaunchVerificationButton } from "@/components/verification/launch-verification-button";

export function FinalCtaSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
      <div className="border border-line/70 bg-panel px-6 py-12 text-center shadow-panel sm:px-10">
        <p className="text-[0.68rem] uppercase tracking-[0.32em] text-accent">
          Ready to verify
        </p>
        <h2 className="mt-4 font-headline text-4xl font-black uppercase tracking-tight text-foreground sm:text-6xl">
          Start a live session
        </h2>
        <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-muted-foreground">
          Launch the client flow, complete the challenge sequence, and receive a clean
          attestation result without operator-only telemetry.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <LaunchVerificationButton label="Initialize session" />
          <Link
            className="inline-flex items-center justify-center border border-line bg-background/70 px-5 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-foreground transition hover:border-accent hover:text-accent"
            href="/app"
          >
            Preview app shell
          </Link>
        </div>
      </div>
    </section>
  );
}

import Link from "next/link";
import type { SessionRecordResponse } from "@sui-human/shared";
import { LaunchVerificationButton } from "@/components/verification/launch-verification-button";
import {
  deriveResultOutcome,
  humanizeFailureReason,
} from "@/features/verifier-core/lib/client-flow";
import { challengeLabel } from "@/features/verifier-core/lib/utils";

function formatDate(value: string | undefined) {
  if (!value) return "Unavailable";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function ResultSummary(props: {
  session: SessionRecordResponse | null;
  sessionId: string;
}) {
  const result = props.session?.result;
  const outcome = deriveResultOutcome(props.session);

  const title =
    outcome === "verified"
      ? "Identity attested"
      : outcome === "expired"
        ? "Session expired"
        : outcome === "spoof"
          ? "Presentation attack detected"
        : outcome === "failed"
          ? "Verification failed"
          : "Session unavailable";

  const body =
    outcome === "verified"
      ? "The verifier accepted the session and returned a successful attestation."
      : outcome === "expired"
        ? "This session is no longer active. Start a new verification to continue."
        : outcome === "spoof"
          ? result?.attack_analysis?.note ??
            "The verifier rejected this session because it resembles a replay, synthetic, or manipulated presentation."
        : outcome === "failed"
          ? humanizeFailureReason(result?.failure_reason)
          : "We could not load a result for this session.";

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6">
        <div className="border border-line/70 bg-panel p-8 shadow-panel sm:p-10">
          <p className="text-[0.68rem] uppercase tracking-[0.32em] text-accent">
            Result / {props.sessionId}
          </p>
          <h1 className="mt-4 font-headline text-4xl font-black uppercase tracking-tight text-foreground sm:text-6xl">
            {title}
          </h1>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-muted-foreground">{body}</p>

          <div className="mt-10 grid gap-0 border border-line/70 sm:grid-cols-2">
            <div className="border-b border-line/70 bg-background/70 p-5 sm:border-b-0 sm:border-r">
              <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                Session status
              </p>
              <p className="mt-3 font-headline text-2xl font-bold uppercase tracking-tight text-foreground">
                {result?.status ?? props.session?.status ?? "unknown"}
              </p>
            </div>
            <div className="bg-background/70 p-5">
              <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                Challenge sequence
              </p>
              <p className="mt-3 text-sm leading-7 text-foreground">
                {props.session?.challenge_sequence?.length
                  ? props.session.challenge_sequence.map((step) => challengeLabel(step)).join(" / ")
                  : "Unavailable"}
              </p>
            </div>
          </div>

          {result?.status === "verified" ? (
            <div className="mt-6 grid gap-0 border border-line/70 sm:grid-cols-2">
              <div className="border-b border-line/70 bg-panel p-5 sm:border-b-0 sm:border-r">
                <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                  Confidence
                </p>
                <p className="mt-3 font-headline text-3xl font-bold uppercase tracking-tight text-foreground">
                  {Math.round(result.confidence * 100)}%
                </p>
              </div>
              <div className="bg-panel p-5">
                <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                  Proof reference
                </p>
                <p className="mt-3 break-all text-sm leading-7 text-foreground">
                  {result.proof_id ?? "Pending"}
                </p>
              </div>
            </div>
          ) : null}

          <dl className="mt-6 grid gap-4 text-sm text-muted-foreground sm:grid-cols-2">
            <div className="border border-line/70 p-4">
              <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Expires</dt>
              <dd className="mt-2 text-foreground">
                {formatDate(result?.expires_at ?? props.session?.expires_at)}
              </dd>
            </div>
            {result?.status === "verified" ? (
              <div className="border border-line/70 p-4">
                <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Session reference</dt>
                <dd className="mt-2 text-foreground">
                  {props.sessionId}
                </dd>
              </div>
            ) : null}
            {result?.status && result.status !== "verified" ? (
              <div className="border border-line/70 p-4">
                <dt className="text-[0.62rem] uppercase tracking-[0.24em]">What to do next</dt>
                <dd className="mt-2 break-words text-foreground">
                  Start a fresh session, use steady lighting, and complete each live instruction before finalizing.
                </dd>
              </div>
            ) : null}
          </dl>

          <div className="mt-8 flex flex-wrap gap-3">
            <LaunchVerificationButton label="Start new session" />
            <Link
              className="inline-flex items-center justify-center border border-line px-5 py-3 text-[0.7rem] uppercase tracking-[0.28em] transition hover:border-accent hover:text-accent"
              href="/app"
            >
              Back to app
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}

"use client";

import Link from "next/link";
import { AppShell } from "@/components/chrome/app-shell";
import { ConsolePanel } from "@/components/chrome/console-panel";
import { WalletSummaryCard } from "@/components/wallet/wallet-summary-card";
import { useAppSession } from "@/features/verifier-core/hooks/use-app-session";
import { useSuiWallet } from "@/features/wallet/hooks/use-sui-wallet";

export function MainAppPage() {
  const wallet = useSuiWallet();
  const { clearSession, error, loadState, restoreStoredSession, routeTarget, session, sessionCopy, startSession } =
    useAppSession();

  const isLoading = loadState === "loading" || loadState === "starting";
  const hasSavedSession = Boolean(session);

  return (
    <AppShell
      activeSection="main_app"
      aside={
        <>
          <ConsolePanel accent="signal" eyebrow="Live / Telemetry" title="System feed">
            <dl className="grid gap-3">
              {[
                { label: "Session state", value: sessionCopy.badge },
                { label: "Route target", value: routeTarget.kind.toUpperCase() },
                { label: "Saved session", value: session?.session_id ?? "NONE" },
              ].map((item) => (
                <div
                  className="flex items-center justify-between border border-line/50 bg-background/60 px-3 py-3"
                  key={item.label}
                >
                  <dt className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                    {item.label}
                  </dt>
                  <dd className="font-headline text-lg font-bold uppercase tracking-tight text-foreground">
                    {item.value}
                  </dd>
                </div>
              ))}
            </dl>
          </ConsolePanel>

          <ConsolePanel accent="neutral" eyebrow="Queue / Next" title="Flow staging">
            <div className="grid gap-3 text-[0.68rem] uppercase tracking-[0.24em] text-muted-foreground">
              <div className="border border-line/50 bg-background/60 px-3 py-3 text-foreground">
                1. Launch from dashboard or restore saved session
              </div>
              <div className="border border-line/50 bg-background/60 px-3 py-3">
                2. Complete the live challenge flow in `/verify/[sessionId]`
              </div>
              <div className="border border-line/50 bg-background/60 px-3 py-3">
                3. Return to the result and proof handoff surfaces
              </div>
            </div>
          </ConsolePanel>

          <ConsolePanel accent="accent" eyebrow="Routing / Links" title="Explore surfaces">
            <div className="grid gap-3 text-[0.68rem] uppercase tracking-[0.24em]">
              <Link className="border border-line/50 bg-background/60 px-3 py-3 transition hover:border-accent hover:text-accent" href="/overview">
                Overview page
              </Link>
              <Link className="border border-line/50 bg-background/60 px-3 py-3 transition hover:border-accent hover:text-accent" href="/about">
                About page
              </Link>
              <Link className="border border-line/50 bg-background/60 px-3 py-3 transition hover:border-accent hover:text-accent" href="/admin">
                Admin console
              </Link>
            </div>
          </ConsolePanel>
        </>
      }
      description="This dashboard is now the wallet-gated app entry surface. It restores saved sessions for this device, routes active work back into live verification, and keeps expired or completed sessions from getting lost."
      eyebrow="Client / Main app"
      meta={[
        { label: "Session mode", value: wallet.isConnected ? "Wallet-bound" : "Wallet-gated" },
        { label: "Capture", value: routeTarget.kind === "verify" ? "Redirecting" : "Standby" },
        {
          label: "Wallet",
          value: wallet.isConnected ? wallet.shortAddress.toUpperCase() : "DISCONNECTED",
        },
      ]}
      title="Identity Attestation"
    >
      <ConsolePanel accent="accent" eyebrow="Scanner / Stage" title="Verification viewport">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div className="relative overflow-hidden border border-accent/30 bg-black p-3">
            <div className="absolute left-0 top-0 h-4 w-4 border-l-2 border-t-2 border-accent" />
            <div className="absolute right-0 top-0 h-4 w-4 border-r-2 border-t-2 border-accent" />
            <div className="absolute bottom-0 left-0 h-4 w-4 border-b-2 border-l-2 border-accent" />
            <div className="absolute bottom-0 right-0 h-4 w-4 border-b-2 border-r-2 border-accent" />
            <div className="scanlines relative grid aspect-video place-items-center bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.12),transparent_38%),linear-gradient(135deg,rgba(0,85,255,0.22),transparent_58%)]">
              <div className="absolute inset-x-0 top-1/2 h-px bg-accent/40" />
              <div className="absolute left-1/2 top-0 h-full w-px bg-accent/30" />
              <div className="grid gap-3 text-center">
                <p className="font-headline text-4xl font-black uppercase tracking-tight text-white">
                  {isLoading ? "Restoring session" : "Command center"}
                </p>
                <p className="max-w-md text-sm leading-7 text-white/70">
                  {sessionCopy.detail}
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-4">
            <div className="border border-line/60 bg-background/60 p-4">
              <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                Current status
              </p>
              <p className="mt-3 font-headline text-2xl font-black uppercase tracking-tight text-foreground">
                {sessionCopy.title}
              </p>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">
                {error
                  ? error
                  : !wallet.isConnected
                    ? "A connected Sui wallet is now the entry condition for creating fresh sessions. Connect first, then this dashboard can mint a wallet-bound verification session."
                  : routeTarget.kind === "verify"
                    ? "An active verification exists. The dashboard will send you back into the live capture route."
                    : routeTarget.kind === "result"
                      ? "A terminal result was found. The dashboard will hand you off to the result view."
                      : routeTarget.kind === "expired"
                        ? "The saved session expired, so the dashboard stays here and offers a clean restart."
                        : "No saved session is blocking progress, so you can safely launch a new verification."}
              </p>
            </div>

            <div className="border border-line/60 bg-background/60 p-4">
              <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                Action rail
              </p>
              <div className="mt-4 grid gap-3">
                {wallet.isConnected ? (
                  <button
                    className="inline-flex items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={isLoading}
                    onClick={() => void startSession(wallet.address)}
                    type="button"
                  >
                    {loadState === "starting" ? "Starting..." : "Verify identity"}
                  </button>
                ) : (
                  <WalletSummaryCard />
                )}
                {hasSavedSession ? (
                  <button
                    className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
                    disabled={isLoading}
                    onClick={() => {
                      void restoreStoredSession();
                    }}
                    type="button"
                  >
                    Refresh saved session
                  </button>
                ) : null}
                {routeTarget.kind === "expired" || hasSavedSession ? (
                  <button
                    className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
                    disabled={isLoading}
                    onClick={clearSession}
                    type="button"
                  >
                    Clear saved session
                  </button>
                ) : null}
                <Link
                  className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
                  href="/overview"
                >
                  Read overview
                </Link>
              </div>
            </div>
          </div>
        </div>
      </ConsolePanel>

      <section className="grid gap-4 lg:grid-cols-3">
        <ConsolePanel accent="signal" eyebrow="Module / One" title="Instruction stack">
          <p className="text-sm leading-7 text-muted-foreground">
            The live challenge queue remains concentrated in the dedicated `/verify/[sessionId]`
            route so this dashboard stays focused on launching, restoring, and proof handoff.
          </p>
        </ConsolePanel>
        <ConsolePanel accent="accent" eyebrow="Module / Two" title="Wallet handoff">
          <p className="text-sm leading-7 text-muted-foreground">
            Wallet login is now the public entry point for starting new sessions. The next step is
            proof claiming and post-verification asset handoff once the backend mint flow is ready.
          </p>
        </ConsolePanel>
        <ConsolePanel accent="neutral" eyebrow="Module / Three" title="Protocol notes">
          <p className="text-sm leading-7 text-muted-foreground">
            Keep technical context visible without exposing backend logs. This screen should feel
            like a client dashboard, not a leaked copy of the admin console.
          </p>
        </ConsolePanel>
      </section>
    </AppShell>
  );
}

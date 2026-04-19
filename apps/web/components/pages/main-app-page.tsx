"use client";

import Link from "next/link";
import { AppShell } from "@/components/chrome/app-shell";
import { ConsolePanel } from "@/components/chrome/console-panel";
import { WalletSummaryCard } from "@/components/wallet/wallet-summary-card";
import { useAppSession } from "@/features/verifier-core/hooks/use-app-session";
import {
  buildSuiscanObjectUrl,
  buildSuiscanTransactionUrl,
} from "@/features/verifier-core/lib/sui-explorer";
import { challengeLabel } from "@/features/verifier-core/lib/utils";
import { useSuiWallet } from "@/features/wallet/hooks/use-sui-wallet";

type DashboardAction =
  | {
      label: string;
      href: string;
    }
  | {
      label: string;
      onClick: () => void;
      disabled?: boolean;
    };

function formatSessionStamp(value: string | undefined | null) {
  if (!value) return "Unavailable";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export function MainAppPage() {
  const wallet = useSuiWallet();
  const {
    clearSession,
    error,
    loadState,
    restoreStoredSession,
    routeTarget,
    session,
    sessionCopy,
    startSession,
  } = useAppSession();

  const isLoading = loadState === "loading" || loadState === "starting";
  const hasSavedSession = Boolean(session);
  const verificationLocked = !wallet.isConnected || isLoading;
  const sessionRouteHref =
    routeTarget.kind === "verify" || routeTarget.kind === "result" || routeTarget.kind === "expired"
      ? routeTarget.href
      : null;
  const latestProof = session?.result?.proof_id ? session.result : null;
  const proofObjectUrl = buildSuiscanObjectUrl(
    latestProof?.proof_id,
    latestProof?.chain_network,
  );
  const proofTransactionUrl = buildSuiscanTransactionUrl(
    latestProof?.transaction_digest,
    latestProof?.chain_network,
  );

  const statusTitle = error
    ? "Attention needed"
    : routeTarget.kind === "verify"
      ? "Verification in progress"
      : routeTarget.kind === "result"
        ? "Proof receipt ready"
        : routeTarget.kind === "expired"
          ? "Previous session expired"
          : wallet.isConnected
            ? "Ready to verify"
            : "Connect to begin";

  const statusDetail = error
    ? error
    : routeTarget.kind === "verify"
      ? "A saved live session already exists for this device. We will route you back into capture so you can finish the challenge and mint flow without restarting."
      : routeTarget.kind === "result"
        ? "The previous verification already reached a terminal result. Review the minted proof receipt here, inspect it on SuiScan, or review the dedicated result screen before starting over."
        : routeTarget.kind === "expired"
          ? "The saved session can no longer continue. Start a fresh verification when you are ready."
          : wallet.isConnected
            ? "Your wallet is connected and the product flow is unlocked. Start a verification, complete the challenge route, then return here to inspect the minted proof receipt."
            : "This product flow is wallet-first. Connect a Sui wallet before creating a verification session so minting and ownership stay aligned.";

  const primaryAction: DashboardAction = error
    ? {
        label: "Retry saved session",
        onClick: () => {
          void restoreStoredSession();
        },
        disabled: isLoading,
      }
    : routeTarget.kind === "verify"
      ? {
          label: "Continue verification",
          href: sessionRouteHref ?? "/app",
        }
      : {
          label: loadState === "starting" ? "Starting..." : "Start verification",
          onClick: () => {
            void startSession(wallet.address);
          },
          disabled: verificationLocked,
        };

  const secondaryActions: DashboardAction[] = [];
  if ((routeTarget.kind === "result" || routeTarget.kind === "expired") && sessionRouteHref) {
    secondaryActions.push({
      label: "Review last result",
      href: sessionRouteHref,
    });
  }
  if (wallet.isConnected) {
    secondaryActions.push({
      label: "Review proof receipt",
      href: "#proof-receipt",
    });
  }
  if (hasSavedSession) {
    secondaryActions.push({
      label: "Refresh saved session",
      onClick: () => {
        void restoreStoredSession();
      },
      disabled: isLoading,
    });
  }
  if (hasSavedSession || routeTarget.kind === "expired") {
    secondaryActions.push({
      label: "Clear saved session",
      onClick: clearSession,
      disabled: isLoading,
    });
  }

  const sequenceLabel =
    session?.challenge_sequence?.length
      ? session.challenge_sequence.map((step) => challengeLabel(step)).join(" / ")
      : "Awaiting session";

  return (
    <AppShell
      activeSection="main_app"
      aside={
        <>
          <ConsolePanel accent="signal" eyebrow="Journey / State" title="Live app state">
            <dl className="grid gap-3">
              {[
                { label: "Session state", value: sessionCopy.badge },
                { label: "Next route", value: routeTarget.kind.toUpperCase() },
                { label: "Wallet", value: wallet.isConnected ? wallet.shortAddress.toUpperCase() : "CONNECT" },
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

          <ConsolePanel accent="neutral" eyebrow="Flow / Promise" title="What happens next">
            <div className="grid gap-3 text-[0.68rem] uppercase tracking-[0.24em] text-muted-foreground">
              <div className="border border-line/50 bg-background/60 px-3 py-3 text-foreground">
                1. Connect wallet and launch from this app
              </div>
              <div className="border border-line/50 bg-background/60 px-3 py-3">
                2. Complete the live capture route and finalize the verifier decision
              </div>
              <div className="border border-line/50 bg-background/60 px-3 py-3">
                3. Mint the proof and verify it on SuiScan
              </div>
            </div>
          </ConsolePanel>

          <ConsolePanel accent="accent" eyebrow="Explore / Support" title="Other surfaces">
            <div className="grid gap-3 text-[0.68rem] uppercase tracking-[0.24em]">
              <Link
                className="border border-line/50 bg-background/60 px-3 py-3 transition hover:border-accent hover:text-accent"
                href="/overview"
              >
                Overview page
              </Link>
              <Link
                className="border border-line/50 bg-background/60 px-3 py-3 transition hover:border-accent hover:text-accent"
                href="/about"
              >
                About page
              </Link>
              <Link
                className="border border-line/50 bg-background/60 px-3 py-3 transition hover:border-accent hover:text-accent"
                href="/admin"
              >
                Admin harness
              </Link>
            </div>
          </ConsolePanel>
        </>
      }
      description="This is the canonical user journey now: connect your wallet, complete live verification, mint the proof, then return here for a simple proof receipt and SuiScan links while the wallet-signed mint flow is being rebuilt."
      eyebrow="Client / Canonical app"
      meta={[
        { label: "Entry mode", value: "Wallet-first" },
        { label: "Verification", value: routeTarget.kind === "verify" ? "Resuming" : "Ready" },
        { label: "Receipt", value: latestProof ? "Available" : "Awaiting mint" },
      ]}
      title="Proof Of Human Journey"
    >
      <ConsolePanel accent="accent" eyebrow="Mission / Launch" title="Verification mission control">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_20rem]">
          <div className="grid gap-6">
            <div className="relative overflow-hidden border border-accent/30 bg-black p-4">
              <div className="absolute left-0 top-0 h-4 w-4 border-l-2 border-t-2 border-accent" />
              <div className="absolute right-0 top-0 h-4 w-4 border-r-2 border-t-2 border-accent" />
              <div className="absolute bottom-0 left-0 h-4 w-4 border-b-2 border-l-2 border-accent" />
              <div className="absolute bottom-0 right-0 h-4 w-4 border-b-2 border-r-2 border-accent" />
              <div className="scanlines relative grid aspect-[16/9] place-items-center bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.12),transparent_36%),linear-gradient(135deg,rgba(0,85,255,0.24),transparent_58%)] px-6">
                <div className="absolute inset-x-0 top-1/2 h-px bg-accent/40" />
                <div className="absolute left-1/2 top-0 h-full w-px bg-accent/30" />
                <div className="grid max-w-2xl gap-4 text-center">
                  <p className="font-headline text-4xl font-black uppercase tracking-tight text-white sm:text-5xl">
                    {isLoading ? "Preparing your route" : statusTitle}
                  </p>
                  <p className="text-sm leading-7 text-white/72 sm:text-base">{statusDetail}</p>
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              {[
                {
                  label: "Wallet ownership",
                  value: wallet.isConnected ? wallet.shortAddress : "Connect wallet",
                  detail: wallet.isConnected
                    ? `Mint target is locked to ${wallet.networkLabel}.`
                    : "Wallet connection is required before a product session can start.",
                },
                {
                  label: "Challenge sequence",
                  value: sequenceLabel,
                  detail: session?.session_id
                    ? `Session ${session.session_id} is the active browser record.`
                    : "A fresh session will receive the verifier challenge queue.",
                },
                {
                  label: "Proof receipt",
                  value: latestProof ? "Available" : "Awaiting mint",
                  detail:
                    "After mint succeeds, this app surface becomes the receipt with direct explorer links.",
                },
              ].map((item) => (
                <div className="border border-line/60 bg-background/60 p-4" key={item.label}>
                  <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                    {item.label}
                  </p>
                  <p className="mt-3 font-headline text-xl font-black uppercase tracking-tight text-foreground">
                    {item.value}
                  </p>
                  <p className="mt-3 text-sm leading-7 text-muted-foreground">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4">
            <div className="border border-line/60 bg-background/60 p-4">
              <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                Primary action
              </p>
              <div className="mt-4 grid gap-3">
                {"href" in primaryAction ? (
                  <Link
                    className="inline-flex items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition hover:brightness-110"
                    href={primaryAction.href}
                  >
                    {primaryAction.label}
                  </Link>
                ) : wallet.isConnected ? (
                  <button
                    className="inline-flex items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={primaryAction.disabled}
                    onClick={primaryAction.onClick}
                    type="button"
                  >
                    {primaryAction.label}
                  </button>
                ) : (
                  <WalletSummaryCard />
                )}

                {secondaryActions.map((action) =>
                  "href" in action ? (
                    <Link
                      className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
                      href={action.href}
                      key={action.label}
                    >
                      {action.label}
                    </Link>
                  ) : (
                    <button
                      className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={action.disabled}
                      key={action.label}
                      onClick={action.onClick}
                      type="button"
                    >
                      {action.label}
                    </button>
                  ),
                )}
              </div>
            </div>

            <div className="border border-line/60 bg-background/60 p-4">
              <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                Session snapshot
              </p>
              <dl className="mt-4 grid gap-4 text-sm text-muted-foreground">
                <div>
                  <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Saved session</dt>
                  <dd className="mt-2 break-words text-foreground">
                    {session?.session_id ?? "No session stored"}
                  </dd>
                </div>
                <div>
                  <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Created</dt>
                  <dd className="mt-2 text-foreground">{formatSessionStamp(session?.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Expires</dt>
                  <dd className="mt-2 text-foreground">{formatSessionStamp(session?.expires_at)}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </ConsolePanel>

      <section className="grid gap-4 lg:grid-cols-3">
        <ConsolePanel accent="signal" eyebrow="Stage / One" title="Connect and commit">
          <p className="text-sm leading-7 text-muted-foreground">
            Wallet-first is the product rule. It keeps the verification subject, minted proof, and
            future wallet-signed claim flow aligned from the first step.
          </p>
        </ConsolePanel>
        <ConsolePanel accent="accent" eyebrow="Stage / Two" title="Verify and mint">
          <p className="text-sm leading-7 text-muted-foreground">
            The live challenge route stays focused on camera capture, final verifier approval, and
            minting. Proof metadata is surfaced as a simple receipt instead of depending on the owner dashboard.
          </p>
        </ConsolePanel>
        <ConsolePanel accent="neutral" eyebrow="Stage / Three" title="Return and verify">
          <p className="text-sm leading-7 text-muted-foreground">
            Come back here to inspect the proof id, transaction digest, Walrus references, and
            jump straight to SuiScan while the wallet-signed mint flow is redesigned.
          </p>
        </ConsolePanel>
      </section>

      <div id="proof-receipt">
        <ConsolePanel accent="signal" eyebrow="Receipt / Minted proof" title="Proof receipt">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {[
                { label: "Proof id", value: latestProof?.proof_id ?? "Unavailable" },
                {
                  label: "Transaction digest",
                  value: latestProof?.transaction_digest ?? "Unavailable",
                },
                { label: "Operation", value: latestProof?.proof_operation ?? "Unavailable" },
                { label: "Chain network", value: latestProof?.chain_network ?? "Unavailable" },
                { label: "Walrus blob id", value: latestProof?.walrus_blob_id ?? "Unavailable" },
                { label: "Seal identity", value: latestProof?.seal_identity ?? "Unavailable" },
              ].map((item) => (
                <div className="border border-line/60 bg-background/60 p-4" key={item.label}>
                  <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                    {item.label}
                  </p>
                  <p className="mt-3 break-words text-sm leading-7 text-foreground">{item.value}</p>
                </div>
              ))}
            </div>

            <div className="border border-line/60 bg-background/60 p-4">
              <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                Explorer links
              </p>
              <div className="mt-4 grid gap-3">
                {proofObjectUrl ? (
                  <Link
                    className="inline-flex items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition hover:brightness-110"
                    href={proofObjectUrl}
                    rel="noreferrer"
                    target="_blank"
                  >
                    View proof on SuiScan
                  </Link>
                ) : null}
                {proofTransactionUrl ? (
                  <Link
                    className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
                    href={proofTransactionUrl}
                    rel="noreferrer"
                    target="_blank"
                  >
                    View transaction
                  </Link>
                ) : null}
                {!proofObjectUrl && !proofTransactionUrl ? (
                  <p className="text-sm leading-7 text-muted-foreground">
                    No minted proof is attached to the current saved session yet.
                  </p>
                ) : (
                  <p className="text-sm leading-7 text-muted-foreground">
                    This temporary receipt flow replaces the broken owner dashboard until the wallet-signed mint flow lands.
                  </p>
                )}
              </div>
            </div>
          </div>
        </ConsolePanel>
      </div>
    </AppShell>
  );
}

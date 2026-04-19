"use client";

import { useMemo, useState } from "react";
import { ConsolePanel } from "@/components/chrome/console-panel";
import { deriveOwnerDecryptPanelStatus } from "@/features/proof-access/lib/panel-state";
import type { RetainedEvidenceBlob } from "@/features/proof-access/lib/types";
import { useOwnerProof } from "@/features/proof-access/hooks/use-owner-proof";

function formatDateTime(value: number | string | null | undefined) {
  if (value == null || value === "") {
    return "Unavailable";
  }

  const date = typeof value === "number" ? new Date(value) : new Date(value);
  return Number.isNaN(date.getTime()) ? "Unavailable" : date.toLocaleString();
}

function formatConfidenceBps(value: number | null | undefined) {
  if (value == null) return "Unavailable";
  return `${(value / 100).toFixed(2)}%`;
}

function readNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readString(value: unknown) {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function readStringList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string" && item.length > 0)
    : [];
}

function buildCuratedEvidenceRows(evidence: RetainedEvidenceBlob) {
  const confidence = readNumber(evidence.verdict_context?.confidence);
  const humanStatus = evidence.verdict_context?.human === true ? "Human" : "Review required";
  const spoofFinal = readNumber(evidence.antispoof_summary?.final_score);
  const deepfakeScore = readNumber(evidence.deepfake_summary?.score);
  const humanFaceScore = readNumber(evidence.human_face_summary?.score);
  const challengeSequence = readStringList(evidence.challenge_sequence);
  const attackFamily = readString(evidence.attack_analysis?.suspected_attack_family);
  const failureCategory = readString(evidence.attack_analysis?.failure_category);

  return [
    { label: "Session id", value: evidence.session_id },
    { label: "Wallet", value: evidence.wallet_address },
    { label: "Challenge type", value: evidence.challenge_type },
    {
      label: "Challenge sequence",
      value: challengeSequence.length > 0 ? challengeSequence.join(" -> ") : "Unavailable",
    },
    { label: "Session started", value: formatDateTime(evidence.session_started_at) },
    { label: "Session completed", value: formatDateTime(evidence.session_completed_at) },
    {
      label: "Verdict confidence",
      value: confidence == null ? "Unavailable" : `${(confidence * 100).toFixed(2)}%`,
    },
    { label: "Verdict", value: humanStatus },
    {
      label: "Spoof summary",
      value: spoofFinal == null ? "Unavailable" : spoofFinal.toFixed(4),
    },
    {
      label: "Deepfake summary",
      value: deepfakeScore == null ? "Unavailable" : deepfakeScore.toFixed(4),
    },
    {
      label: "Human-face summary",
      value: humanFaceScore == null ? "Unavailable" : humanFaceScore.toFixed(4),
    },
    { label: "Frame hashes", value: String(evidence.frame_hashes.length) },
    {
      label: "Verifier bundle",
      value: evidence.model_hashes.verifier_bundle ?? "Unavailable",
    },
    {
      label: "Attack analysis",
      value:
        attackFamily || failureCategory
          ? [attackFamily, failureCategory].filter(Boolean).join(" / ")
          : "Unavailable",
    },
  ];
}

function renderStateCopy(status: ReturnType<typeof deriveOwnerDecryptPanelStatus>) {
  switch (status) {
    case "wallet_disconnected":
      return {
        title: "Connect a wallet",
        detail:
          "The owner decrypt flow is wallet-gated. Connect the wallet that owns the proof before the dashboard can look up evidence.",
      };
    case "config_missing":
      return {
        title: "Public config missing",
        detail:
          "This dashboard is missing the public package, Seal, or Walrus settings required for owner-side retrieval.",
      };
    case "loading_proof":
      return {
        title: "Checking owned proofs",
        detail:
          "The app is querying Sui for the latest active ProofOfHuman owned by the connected wallet.",
      };
    case "no_active_proof":
      return {
        title: "No active proof found",
        detail:
          "This wallet does not currently own an active proof on-chain, so there is nothing to decrypt yet.",
      };
    case "proof_ready":
      return {
        title: "Proof ready for decrypt",
        detail:
          "The latest active proof is loaded. When you continue, the wallet signs a Seal session key and the browser decrypts the Walrus ciphertext locally.",
      };
    case "awaiting_wallet_approval":
      return {
        title: "Awaiting wallet approval",
        detail:
          "Approve the session-key signature in your wallet. Nothing is being written on-chain in this step.",
      };
    case "decrypting":
      return {
        title: "Decrypting evidence",
        detail:
          "The dashboard is fetching the Walrus ciphertext and asking Seal to decrypt it in the browser.",
      };
    case "decrypted":
      return {
        title: "Evidence unlocked",
        detail:
          "The retained evidence payload is now available in memory for this tab only. It is not being persisted locally.",
      };
    case "decrypt_failed":
      return {
        title: "Decrypt failed",
        detail:
          "The proof lookup succeeded, but the owner approval, Walrus fetch, or Seal decrypt step failed. You can retry without reloading the page.",
      };
    case "proof_error":
      return {
        title: "Proof lookup failed",
        detail:
          "The dashboard could not retrieve or decode owned proof metadata from Sui. Check the network, package id, and wallet ownership.",
      };
  }
}

function EvidenceSummary({ evidence }: { evidence: RetainedEvidenceBlob }) {
  const rows = useMemo(() => buildCuratedEvidenceRows(evidence), [evidence]);
  const [showRawJson, setShowRawJson] = useState(false);

  return (
    <div className="grid gap-4">
      <dl className="grid gap-3 md:grid-cols-2">
        {rows.map((row) => (
          <div className="border border-line/60 bg-background/60 px-4 py-4" key={row.label}>
            <dt className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
              {row.label}
            </dt>
            <dd className="mt-3 break-words text-sm leading-7 text-foreground">{row.value}</dd>
          </div>
        ))}
      </dl>

      <div className="border border-line/60 bg-background/60 px-4 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
              Debug / Raw payload
            </p>
            <p className="mt-2 text-sm leading-7 text-muted-foreground">
              Raw decrypted JSON stays hidden unless you explicitly reveal it.
            </p>
          </div>
          <button
            className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
            onClick={() => setShowRawJson((value) => !value)}
            type="button"
          >
            {showRawJson ? "Hide raw JSON" : "Show raw JSON"}
          </button>
        </div>
        {showRawJson ? (
          <pre className="mt-4 max-h-[28rem] overflow-auto border border-line/50 bg-black/40 p-4 text-xs leading-6 text-white/80">
            {JSON.stringify(evidence, null, 2)}
          </pre>
        ) : null}
      </div>
    </div>
  );
}

export function OwnerProofPanel() {
  const {
    config,
    decryptError,
    decryptLatestProof,
    decryptState,
    decryptedEvidence,
    latestProof,
    proofError,
    proofLoadState,
    wallet,
  } = useOwnerProof();

  const status = deriveOwnerDecryptPanelStatus({
    isWalletConnected: wallet.isConnected,
    proofLoadState,
    decryptState,
  });
  const copy = renderStateCopy(status);
  const canDecrypt = status === "proof_ready" || status === "decrypt_failed";

  return (
    <ConsolePanel
      accent="signal"
      eyebrow="Dashboard / Proof access"
      title="Proof NFT and sealed evidence"
      description="This dashboard looks up the connected wallet’s latest active proof, confirms the minted metadata, and can decrypt the Walrus-stored retained evidence directly in the browser."
    >
      <div className="grid gap-6">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="border border-line/60 bg-background/60 px-4 py-4">
            <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
              Current state
            </p>
            <p className="mt-3 font-headline text-2xl font-black uppercase tracking-tight text-foreground">
              {copy.title}
            </p>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{copy.detail}</p>
            {proofError ? (
              <p className="mt-4 text-sm leading-7 text-amber-300">{proofError}</p>
            ) : null}
            {decryptError ? (
              <p className="mt-4 text-sm leading-7 text-amber-300">{decryptError}</p>
            ) : null}
            {status === "config_missing" ? (
              <p className="mt-4 text-sm leading-7 text-muted-foreground">
                Missing: {config.missing.join(", ")}
              </p>
            ) : null}
          </div>

          <div className="border border-line/60 bg-background/60 px-4 py-4">
            <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
              Action rail
            </p>
            <div className="mt-4 grid gap-3">
              <button
                className="inline-flex items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!canDecrypt}
                onClick={() => void decryptLatestProof()}
                type="button"
              >
                {decryptState === "awaiting_wallet_approval"
                  ? "Awaiting approval..."
                  : decryptState === "decrypting"
                    ? "Decrypting..."
                    : decryptedEvidence
                      ? "Decrypt again"
                      : "Decrypt evidence"}
              </button>
              <div className="border border-line/50 bg-panel/60 px-3 py-3 text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                Network: {wallet.networkLabel}
              </div>
              <div className="border border-line/50 bg-panel/60 px-3 py-3 text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                Evidence store: {config.walrusAggregatorUrl ?? "Not configured"}
              </div>
            </div>
          </div>
        </div>

        <dl className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {[
            { label: "Proof id", value: latestProof?.proofId ?? "Unavailable" },
            {
              label: "Transaction digest",
              value: latestProof?.transactionDigest ?? "Unavailable",
            },
            { label: "Walrus blob id", value: latestProof?.walrusBlobId ?? "Unavailable" },
            {
              label: "Walrus blob object id",
              value: latestProof?.walrusBlobObjectId ?? "Unavailable",
            },
            { label: "Seal identity", value: latestProof?.sealIdentity ?? "Unavailable" },
            {
              label: "Expires at",
              value: latestProof ? formatDateTime(latestProof.expiresAtMs) : "Unavailable",
            },
            {
              label: "Issued at",
              value: latestProof ? formatDateTime(latestProof.issuedAtMs) : "Unavailable",
            },
            {
              label: "Confidence",
              value: latestProof ? formatConfidenceBps(latestProof.confidenceBps) : "Unavailable",
            },
            {
              label: "Challenge type",
              value: latestProof?.challengeType ?? "Unavailable",
            },
          ].map((item) => (
            <div className="border border-line/60 bg-background/60 px-4 py-4" key={item.label}>
              <dt className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                {item.label}
              </dt>
              <dd className="mt-3 break-words text-sm leading-7 text-foreground">
                {item.value}
              </dd>
            </div>
          ))}
        </dl>

        {decryptedEvidence ? <EvidenceSummary evidence={decryptedEvidence} /> : null}
      </div>
    </ConsolePanel>
  );
}

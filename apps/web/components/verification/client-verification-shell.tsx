"use client";

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SiteHeader } from "@/components/marketing/site-header";
import { LiveCameraStage } from "@/features/verifier-core/components/live-camera-stage";
import { useClientVerificationFlow } from "@/features/verifier-core/hooks/use-client-verification-flow";
import { drawOverlay } from "@/features/verifier-core/lib/landmarks";
import { challengeLabel } from "@/features/verifier-core/lib/utils";

const stateTitles = {
  warming: "Preparing capture",
  camera_idle: "Open your webcam",
  camera_ready: "Ready to verify",
  camera_blocked: "Camera access needed",
  framing: "Center your face",
  challenge_active: "Follow the live instruction",
  ready_to_finalize: "Ready to finalize",
  ready_to_mint: "Verified. Ready to mint",
  processing: "Awaiting final verdict",
  minting: "Minting proof",
  disconnected: "Connection interrupted",
  verified: "Verification complete",
  failed: "Verification failed",
  expired: "Session expired",
} as const;

export default function ClientVerificationShell(props: { sessionId: string }) {
  const router = useRouter();
  const {
    media,
    verifier,
    uiState,
    helperText,
    currentInstruction,
    canOpenCamera,
    canCloseCamera,
    canStartVerification,
    canFinalize,
    canMint,
    openCamera,
    closeCamera,
    startVerification,
    mintProof,
    reconnectSession,
  } =
    useClientVerificationFlow(props.sessionId);

  useEffect(() => {
    drawOverlay({
      video: media.videoRef.current,
      canvas: media.overlayCanvasRef.current,
      face: media.latestFaceRef.current,
      metrics: media.landmarkMetrics,
      debug: verifier.backendDebug,
      stepStatus: verifier.stepStatus,
    });
  }, [media.landmarkMetrics, verifier.backendDebug, verifier.stepStatus, media]);

  useEffect(() => {
    if (!verifier.result) return;
    if (verifier.result.status === "verified" && !verifier.result.proof_id) return;
    router.replace(`/result/${props.sessionId}`);
  }, [props.sessionId, router, verifier.result]);

  const sequenceLabel = useMemo(
    () =>
      verifier.challengeSequence.length > 0
        ? verifier.challengeSequence.map((step) => challengeLabel(step)).join(" / ")
        : "Waiting for session stream",
    [verifier.challengeSequence],
  );

  return (
    <main className="min-h-screen bg-background text-foreground">
      <SiteHeader compact />
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <div className="mb-8 flex flex-col gap-4 border border-line/70 bg-panel p-5 shadow-panel md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-[0.68rem] uppercase tracking-[0.32em] text-accent">
              Session / {props.sessionId}
            </p>
            <h1 className="mt-3 font-headline text-4xl font-black uppercase tracking-tight text-foreground sm:text-5xl">
              {stateTitles[uiState]}
            </h1>
          </div>
          <p className="max-w-xl text-sm leading-7 text-muted-foreground">{helperText}</p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_22rem]">
          <div className="space-y-6">
            <LiveCameraStage
              captureCanvasRef={media.captureCanvasRef}
              detail={verifier.connectionState}
              overlayCanvasRef={media.overlayCanvasRef}
              status={verifier.statusMessage}
              videoRef={media.videoRef}
            />

            <div className="grid gap-4 border border-line/70 bg-panel p-5 shadow-panel sm:grid-cols-3">
              <div>
                <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                  Current instruction
                </p>
                <p className="mt-3 font-headline text-xl font-bold uppercase tracking-tight text-foreground">
                  {verifier.challengeType ? challengeLabel(verifier.challengeType) : "Hold steady"}
                </p>
              </div>
              <div>
                <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                  Sequence
                </p>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{sequenceLabel}</p>
              </div>
              <div>
                <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                  Progress
                </p>
                <p className="mt-3 font-headline text-2xl font-bold uppercase tracking-tight text-foreground">
                  {Math.round(verifier.progress * 100)}%
                </p>
              </div>
            </div>
          </div>

          <aside className="space-y-4">
            <div className="border border-line/70 bg-panel p-5 shadow-panel">
              <p className="text-[0.65rem] uppercase tracking-[0.28em] text-accent">
                Guidance
              </p>
              <h2 className="mt-3 font-headline text-2xl font-bold uppercase tracking-tight text-foreground">
                {currentInstruction}
              </h2>
              <p className="mt-4 text-sm leading-7 text-muted-foreground">{helperText}</p>
            </div>

            <div className="border border-line/70 bg-background/70 p-5">
              <div className="flex items-center justify-between gap-4">
                <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                  Session state
                </p>
                <span className="text-[0.65rem] uppercase tracking-[0.28em] text-signal-cyan">
                  {verifier.connectionState}
                </span>
              </div>
              <dl className="mt-4 grid gap-4 text-sm text-muted-foreground">
                <div>
                  <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Camera</dt>
                  <dd className="mt-1 text-foreground">{media.cameraMessage}</dd>
                </div>
                <div>
                  <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Face tracking</dt>
                  <dd className="mt-1 text-foreground">{media.landmarkMessage}</dd>
                </div>
                <div>
                  <dt className="text-[0.62rem] uppercase tracking-[0.24em]">Verification</dt>
                  <dd className="mt-1 text-foreground">
                    {verifier.captureActive
                      ? "Live checks are running."
                      : verifier.result?.status === "verified" && !verifier.result.proof_id
                        ? "Server approved the session. Proof mint is now available."
                      : verifier.finalizeReady
                        ? "Live checks complete. Ready for final server review."
                      : "Waiting for you to begin verification."}
                  </dd>
                </div>
              </dl>
              <div className="mt-6 space-y-3">
                <div className="border border-line/70 bg-panel p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[0.62rem] uppercase tracking-[0.24em] text-accent">
                        Step 1
                      </p>
                      <p className="mt-2 text-sm font-semibold uppercase tracking-[0.2em] text-foreground">
                        Start verifying
                      </p>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        Open the webcam only when you are ready. You can close it at any time before minting.
                      </p>
                    </div>
                    <span className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                      {media.cameraState === "ready" ? "Ready" : "Pending"}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button
                      className="inline-flex min-w-[10rem] items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={!canOpenCamera}
                      onClick={openCamera}
                      type="button"
                    >
                      Open webcam
                    </button>
                    <button
                      className="inline-flex min-w-[10rem] items-center justify-center border border-line bg-panel px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-foreground transition hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={!canCloseCamera}
                      onClick={closeCamera}
                      type="button"
                    >
                      Close webcam
                    </button>
                  </div>
                </div>

                <div className="border border-line/70 bg-panel p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[0.62rem] uppercase tracking-[0.24em] text-accent">
                        Step 2
                      </p>
                      <p className="mt-2 text-sm font-semibold uppercase tracking-[0.2em] text-foreground">
                        Verify
                      </p>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        Start the live challenge to test motion, spoof, and deepfake signals. This stage only gathers live evidence.
                      </p>
                    </div>
                    <span className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                      {verifier.captureActive
                        ? "Running"
                        : verifier.finalizeReady || verifier.stepStatus === "completed"
                          ? "Complete"
                          : "Pending"}
                    </span>
                  </div>
                  <button
                    className="mt-4 inline-flex w-full items-center justify-center border border-line bg-panel px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-foreground transition hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!canStartVerification}
                    onClick={startVerification}
                    type="button"
                  >
                    {verifier.captureActive ? "Verification running" : "Verify"}
                  </button>
                </div>

                <div className="border border-line/70 bg-panel p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[0.62rem] uppercase tracking-[0.24em] text-accent">
                        Step 3
                      </p>
                      <p className="mt-2 text-sm font-semibold uppercase tracking-[0.2em] text-foreground">
                        Finalize verification
                      </p>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        Submit the session for the server's final verdict. A successful verdict unlocks the mint step.
                      </p>
                    </div>
                    <span className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                      {verifier.result?.status === "verified" && !verifier.result.proof_id
                        ? "Approved"
                        : canFinalize
                          ? "Ready"
                          : verifier.finalizeRequested
                            ? "Submitting"
                            : "Locked"}
                    </span>
                  </div>
                  <button
                    className="mt-4 inline-flex w-full items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!canFinalize}
                    onClick={verifier.sendFinalize}
                    type="button"
                  >
                    {verifier.finalizeRequested ? "Submitting..." : "Finalize verification"}
                  </button>
                </div>

                <div className="border border-line/70 bg-panel p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-[0.62rem] uppercase tracking-[0.24em] text-accent">
                        Step 4
                      </p>
                      <p className="mt-2 text-sm font-semibold uppercase tracking-[0.2em] text-foreground">
                        Mint proof
                      </p>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">
                        Mint the proof only after the server returns a successful final verdict. This step opens your wallet so you can sign the proof transaction directly.
                      </p>
                    </div>
                    <span className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                      {verifier.result?.status === "verified" && verifier.result?.proof_id
                        ? "Complete"
                        : verifier.mintRequested
                          ? "Awaiting wallet"
                          : canMint
                            ? "Ready"
                            : "Locked"}
                    </span>
                  </div>
                  <button
                    className="mt-4 inline-flex w-full items-center justify-center border border-accent bg-accent px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!canMint}
                    onClick={mintProof}
                    type="button"
                  >
                    {verifier.mintRequested ? "Awaiting wallet..." : "Mint proof"}
                  </button>
                </div>
              </div>
              {uiState === "disconnected" ? (
                <button
                  className="mt-3 inline-flex w-full items-center justify-center border border-line bg-panel px-4 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-foreground transition hover:border-accent hover:text-accent"
                  onClick={reconnectSession}
                  type="button"
                >
                  Reconnect session
                </button>
              ) : null}
            </div>

            <div className="border border-line/70 bg-panel p-5">
              <p className="text-[0.65rem] uppercase tracking-[0.28em] text-muted-foreground">
                Need a fresh session?
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Link
                  className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
                  href="/app"
                >
                  Back to app
                </Link>
                <Link
                  className="inline-flex items-center justify-center border border-line px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition hover:border-accent hover:text-accent"
                  href={`/result/${props.sessionId}`}
                >
                  View result
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}

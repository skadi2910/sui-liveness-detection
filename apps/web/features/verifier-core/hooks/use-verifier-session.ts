"use client";

import { useEffect, useRef, useState } from "react";
import type {
  ChallengeType,
  CreateSessionResponse,
  HealthResponse,
  PreparedProofClaim,
  SessionRecordResponse,
  StepStatus,
  VerificationDebugPayload,
  VerificationMode,
  VerificationResult,
  WsServerEvent,
} from "@sui-human/shared";
import {
  autoFinalizeDelayMs,
  captureIntervalMs,
  healthPollIntervalMs,
  httpBase,
  wsBase,
} from "../lib/constants";
import { challengeLabel, normalizeChallengeSequence, normalizeCompletedChallenges } from "../lib/utils";

type AppendLog = (section: "pipeline" | "detection" | "signals", summary: string, detail?: unknown) => void;

type SessionSnapshot = Pick<
  CreateSessionResponse,
  | "session_id"
  | "status"
  | "challenge_type"
  | "challenge_sequence"
  | "current_challenge_index"
  | "total_challenges"
  | "completed_challenges"
  | "expires_at"
> & {
  ws_url: string;
};

export function useVerifierSession(params: {
  walletAddress?: string | null;
  verificationMode: VerificationMode;
  challengeSequenceOverride?: ChallengeType[] | null;
  autoFinalizeOnComplete?: boolean;
  autoCaptureOnSocketOpen?: boolean;
  appendLog: AppendLog;
  appendDebugLogs: (debug: VerificationDebugPayload) => void;
  resetLogs: () => void;
  resetSummary: () => void;
  captureFrame: (socket: WebSocket | null) => void;
  resetCaptureState: () => void;
}) {
  const socketRef = useRef<WebSocket | null>(null);
  const captureTimerRef = useRef<number | null>(null);
  const finalizeTimerRef = useRef<number | null>(null);
  const finalizeRequestedRef = useRef(false);
  const autoFinalizeOnCompleteRef = useRef(params.autoFinalizeOnComplete ?? true);
  const captureEnabledRef = useRef(params.autoCaptureOnSocketOpen ?? true);
  const captureFrameRef = useRef(params.captureFrame);
  const sessionRef = useRef<CreateSessionResponse | null>(null);
  const resultRef = useRef<VerificationResult | null>(null);
  const busyRef = useRef(false);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [session, setSession] = useState<CreateSessionResponse | null>(null);
  const [challengeType, setChallengeType] = useState<ChallengeType | null>(null);
  const [challengeSequence, setChallengeSequence] = useState<ChallengeType[]>([]);
  const [currentChallengeIndex, setCurrentChallengeIndex] = useState(0);
  const [completedChallenges, setCompletedChallenges] = useState<ChallengeType[]>([]);
  const [stepStatus, setStepStatus] = useState<StepStatus>("pending");
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("Waiting for backend.");
  const [backendDebug, setBackendDebug] = useState<VerificationDebugPayload | null>(null);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [connectionState, setConnectionState] = useState("idle");
  const [busy, setBusy] = useState(false);
  const [finalizeRequested, setFinalizeRequested] = useState(false);
  const [mintRequested, setMintRequested] = useState(false);
  const [captureActive, setCaptureActive] = useState(params.autoCaptureOnSocketOpen ?? true);
  const [finalizeReady, setFinalizeReady] = useState(false);
  const modelsReady = health?.models === "ready";

  useEffect(() => {
    autoFinalizeOnCompleteRef.current = params.autoFinalizeOnComplete ?? true;
  }, [params.autoFinalizeOnComplete]);

  useEffect(() => {
    captureEnabledRef.current = params.autoCaptureOnSocketOpen ?? true;
    setCaptureActive(params.autoCaptureOnSocketOpen ?? true);
  }, [params.autoCaptureOnSocketOpen]);

  useEffect(() => {
    captureFrameRef.current = params.captureFrame;
  }, [params.captureFrame]);

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    resultRef.current = result;
  }, [result]);

  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);

  async function fetchHealth() {
    try {
      const response = await fetch(`${httpBase}/api/health`, { cache: "no-store" });
      const payload = (await response.json()) as HealthResponse;
      setHealth(payload);
      if (!socketRef.current && !sessionRef.current && !resultRef.current && !busyRef.current) {
        setStatusMessage(
          payload.models === "ready"
            ? "Backend ready."
            : "Waiting for backend models to finish loading...",
        );
      }
      params.appendLog("pipeline", "Backend health fetched", payload);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Health check failed.";
      if (!socketRef.current && !sessionRef.current && !resultRef.current && !busyRef.current) {
        setStatusMessage("Waiting for backend health...");
      }
      params.appendLog("pipeline", "Health check failed", { message });
    }
  }

  function cleanupSocket() {
    stopCapture({ preserveIntent: true });
    if (finalizeTimerRef.current !== null) {
      window.clearTimeout(finalizeTimerRef.current);
      finalizeTimerRef.current = null;
    }
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    finalizeRequestedRef.current = false;
    setFinalizeRequested(false);
    setMintRequested(false);
    params.resetCaptureState();
  }

  function beginCaptureLoop() {
    if (captureTimerRef.current !== null) {
      return;
    }
    captureTimerRef.current = window.setInterval(() => {
      captureFrameRef.current(socketRef.current);
    }, captureIntervalMs);
  }

  function startCapture() {
    if (finalizeRequestedRef.current || resultRef.current) {
      setStatusMessage("Verification is already finalized for this session.");
      params.appendLog("pipeline", "Capture start blocked", {
        reason: "session_already_finalized",
      });
      return;
    }

    if (finalizeReady) {
      setStatusMessage(
        "Live checks are already complete. Finalize verification to receive the server verdict.",
      );
      params.appendLog("pipeline", "Capture start blocked", {
        reason: "finalize_ready",
      });
      return;
    }

    if (captureTimerRef.current !== null || captureEnabledRef.current) {
      setStatusMessage("Verification is already running. Finish the live challenge before continuing.");
      params.appendLog("pipeline", "Capture start blocked", {
        reason: "capture_already_running",
      });
      return;
    }

    captureEnabledRef.current = true;
    setCaptureActive(true);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      beginCaptureLoop();
      setStatusMessage("Verification in progress. Follow the live challenge guidance.");
      params.appendLog("pipeline", "Capture loop started");
    }
  }

  function stopCapture(options?: { preserveIntent?: boolean }) {
    if (captureTimerRef.current !== null) {
      window.clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }
    if (!options?.preserveIntent) {
      captureEnabledRef.current = false;
      setCaptureActive(false);
      params.appendLog("pipeline", "Capture loop stopped");
    }
  }

  function applySessionSnapshot(snapshot: SessionSnapshot) {
    const normalizedSequence = normalizeChallengeSequence(
      snapshot.challenge_sequence,
      snapshot.challenge_type,
    );
    setSession(snapshot);
    setChallengeType(snapshot.challenge_type);
    setChallengeSequence(normalizedSequence);
    setCurrentChallengeIndex(snapshot.current_challenge_index ?? 0);
    setCompletedChallenges(normalizeCompletedChallenges(snapshot.completed_challenges));
    setStepStatus("pending");
    setFinalizeReady(false);
    setConnectionState("connecting");
    setStatusMessage(
      `Sequence ready: ${normalizedSequence.map(challengeLabel).join(" -> ") || challengeLabel(snapshot.challenge_type)}`,
    );
  }

  function openSessionSocket(snapshot: SessionSnapshot) {
    const websocket = new WebSocket(`${wsBase}${snapshot.ws_url}`);
    socketRef.current = websocket;

    websocket.onopen = () => {
      setConnectionState("open");
      params.appendLog("pipeline", "WebSocket open", { session_id: snapshot.session_id });
      if (captureEnabledRef.current) {
        beginCaptureLoop();
      } else {
        setStatusMessage("Session connected. Open the webcam and press Verify when you are ready.");
      }
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data) as WsServerEvent;

      if (message.type === "session_ready") {
        setStatusMessage(message.payload.message);
        params.appendLog("pipeline", "Session ready", message.payload);
        return;
      }

      if (message.type === "challenge_update" || message.type === "progress") {
        handleProgressLikePayload(message.payload);
        if (message.type === "challenge_update") {
          params.appendLog(
            "pipeline",
            `${(message.payload.current_challenge_index ?? 0) + 1}/${normalizeChallengeSequence(
              message.payload.challenge_sequence,
              message.payload.challenge_type,
            ).length} ${challengeLabel(message.payload.challenge_type)} ${message.payload.step_status}: ${message.payload.message}`,
            message.payload,
          );
        }

        if (message.payload.debug) {
          params.appendDebugLogs(message.payload.debug);
        }

        if (
          autoFinalizeOnCompleteRef.current &&
          message.payload.step_status === "completed" &&
          (message.payload.progress ?? 0) >= 1 &&
          !finalizeRequestedRef.current
        ) {
          if (finalizeTimerRef.current !== null) {
            window.clearTimeout(finalizeTimerRef.current);
          }
          finalizeTimerRef.current = window.setTimeout(() => {
            finalizeTimerRef.current = null;
            sendFinalize();
          }, autoFinalizeDelayMs);
        }
        return;
      }

      if (message.type === "processing") {
        setStatusMessage(message.payload.message);
        params.appendLog("pipeline", "Processing", message.payload);
        return;
      }

      if (message.type === "verified" || message.type === "failed") {
        setResult(message.payload);
        handleProgressLikePayload(message.payload);
        const resultMode = message.payload.evaluation_mode ?? params.verificationMode;
        setStatusMessage(
          message.type === "verified"
            ? `${resultMode.replaceAll("_", " ")} passed.`
            : `${resultMode.replaceAll("_", " ")} failed: ${message.payload.failure_reason ?? "unknown"}`,
        );
        params.appendLog(
          "pipeline",
          message.type === "verified"
            ? "Terminal result: verified"
            : "Terminal result: failed",
          message.payload,
        );
        params.appendLog(
          "signals",
          `Anti-spoof ${message.payload.spoof_score.toFixed(2)} / max ${message.payload.max_spoof_score?.toFixed(2) ?? "n/a"}`,
          message.payload,
        );
        cleanupSocket();
        return;
      }

      if (message.type === "error") {
        setStatusMessage(message.payload.message);
        params.appendLog("pipeline", "Socket error", message.payload);
        cleanupSocket();
      }
    };

    websocket.onerror = () => {
      setConnectionState("error");
      setStatusMessage("WebSocket error");
      params.appendLog("pipeline", "WebSocket error");
    };

    websocket.onclose = () => {
      setConnectionState("closed");
    };
  }

  function handleProgressLikePayload(payload: {
    challenge_type: ChallengeType;
    challenge_sequence: ChallengeType[];
    current_challenge_index?: number;
    completed_challenges?: ChallengeType[];
    step_status?: StepStatus;
    progress?: number;
    finalize_ready?: boolean;
    message?: string;
    debug?: VerificationDebugPayload | null;
  }) {
    setChallengeType(payload.challenge_type);
    setChallengeSequence(
      normalizeChallengeSequence(payload.challenge_sequence, payload.challenge_type),
    );
    setCurrentChallengeIndex(payload.current_challenge_index ?? 0);
    setCompletedChallenges(normalizeCompletedChallenges(payload.completed_challenges));
    if (payload.step_status) setStepStatus(payload.step_status);
    if (typeof payload.progress === "number") setProgress(payload.progress);
    if (typeof payload.finalize_ready === "boolean") setFinalizeReady(payload.finalize_ready);
    if (typeof payload.message === "string") setStatusMessage(payload.message);
    if ("debug" in payload) setBackendDebug(payload.debug ?? null);
  }

  function sendFinalize() {
    if (!modelsReady) {
      setStatusMessage("Finalize unavailable: backend models are still loading.");
      params.appendLog("pipeline", "Finalize blocked", {
        reason: "models_not_ready",
      });
      void fetchHealth();
      return;
    }

    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setStatusMessage("Finalize unavailable: session socket is not open.");
      params.appendLog("pipeline", "Finalize blocked", {
        connection_state: connectionState,
        has_socket: Boolean(socketRef.current),
      });
      return;
    }

    finalizeRequestedRef.current = true;
    setFinalizeRequested(true);
    stopCapture({ preserveIntent: true });
    socketRef.current.send(
      JSON.stringify({
        type: "finalize",
        timestamp: new Date().toISOString(),
        mode: params.verificationMode,
      }),
    );
    params.appendLog("pipeline", "Finalize requested", {
      mode: params.verificationMode,
    });
  }

  async function sendMint() {
    if (!sessionRef.current) {
      setStatusMessage("Mint unavailable: session is not loaded.");
      return;
    }
    if (!resultRef.current || resultRef.current.status !== "verified" || resultRef.current.proof_id) {
      setStatusMessage("Mint unavailable: finalize verification successfully first.");
      return;
    }

    setMintRequested(true);
    setStatusMessage("Minting proof and storing encrypted evidence...");

    try {
      const response = await fetch(`${httpBase}/api/sessions/${sessionRef.current.session_id}/mint`, {
        method: "POST",
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: "Mint failed." }));
        throw new Error(payload.detail ?? "Mint failed.");
      }

      const minted = (await response.json()) as VerificationResult;
      setResult(minted);
      setStatusMessage("Proof minted successfully.");
      params.appendLog("pipeline", "Mint requested", { session_id: sessionRef.current.session_id });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Mint failed.";
      setStatusMessage(message);
      params.appendLog("pipeline", "Mint failed", { message, session_id: sessionRef.current.session_id });
    } finally {
      setMintRequested(false);
    }
  }

  async function prepareMintClaim() {
    if (!sessionRef.current) {
      setStatusMessage("Mint unavailable: session is not loaded.");
      return null;
    }
    if (!resultRef.current || resultRef.current.status !== "verified" || resultRef.current.proof_id) {
      setStatusMessage("Mint unavailable: finalize verification successfully first.");
      return null;
    }

    setMintRequested(true);
    setStatusMessage("Preparing the wallet claim and encrypted evidence receipt...");

    try {
      const response = await fetch(`${httpBase}/api/sessions/${sessionRef.current.session_id}/claim`, {
        method: "POST",
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: "Could not prepare proof claim." }));
        throw new Error(payload.detail ?? "Could not prepare proof claim.");
      }

      const prepared = (await response.json()) as PreparedProofClaim;
      params.appendLog("pipeline", "Wallet claim prepared", {
        session_id: sessionRef.current.session_id,
        operation: prepared.operation,
      });
      setStatusMessage("Approve the wallet transaction to mint the proof.");
      return prepared;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not prepare proof claim.";
      setStatusMessage(message);
      setMintRequested(false);
      params.appendLog("pipeline", "Wallet claim preparation failed", {
        message,
        session_id: sessionRef.current.session_id,
      });
      throw error;
    }
  }

  async function completeMintClaim(transactionDigest: string, proofId?: string | null) {
    if (!sessionRef.current) {
      throw new Error("Mint completion unavailable: session is not loaded.");
    }

    try {
      const response = await fetch(`${httpBase}/api/sessions/${sessionRef.current.session_id}/claim/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transaction_digest: transactionDigest,
          proof_id: proofId ?? undefined,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: "Could not complete proof mint." }));
        throw new Error(payload.detail ?? "Could not complete proof mint.");
      }

      const minted = (await response.json()) as VerificationResult;
      setResult(minted);
      setStatusMessage("Proof minted successfully.");
      params.appendLog("pipeline", "Wallet mint completed", {
        session_id: sessionRef.current.session_id,
        transaction_digest: transactionDigest,
      });
      return minted;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not complete proof mint.";
      setStatusMessage(message);
      params.appendLog("pipeline", "Wallet mint completion failed", {
        message,
        session_id: sessionRef.current.session_id,
        transaction_digest: transactionDigest,
      });
      throw error;
    } finally {
      setMintRequested(false);
    }
  }

  async function cancelMintClaim(reason: string) {
    if (!sessionRef.current) {
      setMintRequested(false);
      return;
    }

    try {
      await fetch(`${httpBase}/api/sessions/${sessionRef.current.session_id}/claim/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      params.appendLog("pipeline", "Wallet mint cancelled", {
        reason,
        session_id: sessionRef.current.session_id,
      });
    } finally {
      setMintRequested(false);
      setStatusMessage(reason);
    }
  }

  async function startSession() {
    if (!params.walletAddress?.trim()) {
      setStatusMessage("Connect a Sui wallet before starting a verification session.");
      params.appendLog("pipeline", "Session start blocked", {
        reason: "wallet_required",
      });
      return;
    }

    if (!modelsReady) {
      setStatusMessage("Backend models are still loading. Please wait a moment.");
      params.appendLog("pipeline", "Session start blocked", {
        reason: "models_not_ready",
        health,
      });
      void fetchHealth();
      return;
    }

    cleanupSocket();
    setBusy(true);
    setResult(null);
    setProgress(0);
    setBackendDebug(null);
    setFinalizeReady(false);
    setChallengeSequence([]);
    setCompletedChallenges([]);
    setCurrentChallengeIndex(0);
    setStepStatus("pending");
    setFinalizeRequested(false);
    captureEnabledRef.current = params.autoCaptureOnSocketOpen ?? true;
    setCaptureActive(params.autoCaptureOnSocketOpen ?? true);
    params.resetSummary();
    params.resetLogs();
    setStatusMessage("Creating session...");

    try {
      const response = await fetch(`${httpBase}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          wallet_address: params.walletAddress,
          client: {
            platform: "web",
            user_agent: navigator.userAgent,
          },
          challenge_sequence:
            params.challengeSequenceOverride && params.challengeSequenceOverride.length > 0
              ? params.challengeSequenceOverride
              : undefined,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(payload.detail ?? "Could not create session");
      }

      const created = (await response.json()) as CreateSessionResponse;
      applySessionSnapshot(created);
      params.appendLog("pipeline", "Session created", created);
      openSessionSocket(created);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Session creation failed.";
      setStatusMessage(message);
      params.appendLog("pipeline", "Session creation failed", { message });
    } finally {
      setBusy(false);
    }
  }

  async function connectToSession(sessionId: string) {
    if (!sessionId) return;

    cleanupSocket();
    setBusy(true);
    setResult(null);
    setBackendDebug(null);
    setFinalizeRequested(false);
    setFinalizeReady(false);
    setStatusMessage("Restoring session...");

    try {
      const response = await fetch(`${httpBase}/api/sessions/${sessionId}`, {
        cache: "no-store",
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(payload.detail ?? "Could not load session");
      }

      const existing = (await response.json()) as SessionRecordResponse;
      const snapshot: SessionSnapshot = {
        session_id: existing.session_id,
        status: existing.status,
        challenge_type: existing.challenge_type,
        challenge_sequence: existing.challenge_sequence,
        current_challenge_index: existing.current_challenge_index,
        total_challenges: existing.total_challenges,
        completed_challenges: existing.completed_challenges,
        expires_at: existing.expires_at,
        ws_url: `/ws/sessions/${existing.session_id}/stream`,
      };

      applySessionSnapshot(snapshot);
      params.appendLog("pipeline", "Session restored", existing);

      if (existing.result) {
        setConnectionState("closed");
        setResult(existing.result);
        handleProgressLikePayload(existing.result);
        setStatusMessage(
          existing.result.status === "verified"
            ? "Verification complete."
            : existing.result.failure_reason ?? "Verification finished.",
        );
        return;
      }

      if (existing.status === "expired") {
        setConnectionState("closed");
        setStatusMessage("This verification session has expired.");
        return;
      }

      openSessionSocket(snapshot);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Session restore failed.";
      setStatusMessage(message);
      params.appendLog("pipeline", "Session restore failed", { message, sessionId });
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void fetchHealth();
    const intervalId = window.setInterval(() => {
      void fetchHealth();
    }, healthPollIntervalMs);
    return () => {
      window.clearInterval(intervalId);
      cleanupSocket();
    };
  }, []);

  return {
    health,
    modelsReady,
    session,
    challengeType,
    challengeSequence,
    currentChallengeIndex,
    completedChallenges,
    stepStatus,
    progress,
    statusMessage,
    backendDebug,
    result,
    connectionState,
    busy,
    finalizeRequested,
    mintRequested,
    captureActive,
    finalizeReady,
    startSession,
    connectToSession,
    startCapture,
    stopCapture,
    sendFinalize,
    sendMint,
    prepareMintClaim,
    completeMintClaim,
    cancelMintClaim,
  };
}

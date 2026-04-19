"use client";

import { useEffect, useRef, useState } from "react";
import type {
  ChallengeType,
  CreateSessionResponse,
  HealthResponse,
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
  walletAddress: string;
  verificationMode: VerificationMode;
  challengeSequenceOverride?: ChallengeType[] | null;
  autoFinalizeOnComplete?: boolean;
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
  const modelsReady = health?.models === "ready";

  useEffect(() => {
    autoFinalizeOnCompleteRef.current = params.autoFinalizeOnComplete ?? true;
  }, [params.autoFinalizeOnComplete]);

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
    if (captureTimerRef.current !== null) {
      window.clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }
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
    params.resetCaptureState();
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
      captureTimerRef.current = window.setInterval(() => {
        captureFrameRef.current(socketRef.current);
      }, captureIntervalMs);
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

  async function startSession() {
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
    setChallengeSequence([]);
    setCompletedChallenges([]);
    setCurrentChallengeIndex(0);
    setStepStatus("pending");
    setFinalizeRequested(false);
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
    startSession,
    connectToSession,
    sendFinalize,
  };
}

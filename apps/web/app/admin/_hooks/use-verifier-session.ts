"use client";

import { useEffect, useRef, useState } from "react";
import type {
  ChallengeType,
  CreateSessionResponse,
  HealthResponse,
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
} from "../_lib/constants";
import { challengeLabel, normalizeChallengeSequence, normalizeCompletedChallenges } from "../_lib/utils";

type AppendLog = (section: "pipeline" | "detection" | "signals", summary: string, detail?: unknown) => void;

export function useVerifierSession(params: {
  walletAddress: string;
  verificationMode: VerificationMode;
  challengeSequenceOverride?: ChallengeType[] | null;
  autoAssist: boolean;
  appendLog: AppendLog;
  appendDebugLogs: (debug: VerificationDebugPayload) => void;
  resetLogs: () => void;
  resetSummary: () => void;
  captureFrame: (
    socket: WebSocket | null,
    options: { includeTrackedSignals: boolean; forceSpoof: boolean },
  ) => void;
  resetCaptureState: () => void;
  forceSpoof: boolean;
}) {
  const socketRef = useRef<WebSocket | null>(null);
  const captureTimerRef = useRef<number | null>(null);
  const finalizeTimerRef = useRef<number | null>(null);
  const finalizeRequestedRef = useRef(false);
  const autoAssistRef = useRef(false);
  const captureFrameRef = useRef(params.captureFrame);
  const forceSpoofRef = useRef(params.forceSpoof);
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
    autoAssistRef.current = params.autoAssist;
  }, [params.autoAssist]);

  useEffect(() => {
    captureFrameRef.current = params.captureFrame;
  }, [params.captureFrame]);

  useEffect(() => {
    forceSpoofRef.current = params.forceSpoof;
  }, [params.forceSpoof]);

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
      const normalizedSequence = normalizeChallengeSequence(
        created.challenge_sequence,
        created.challenge_type,
      );
      setSession(created);
      setChallengeType(created.challenge_type);
      setChallengeSequence(normalizedSequence);
      setCurrentChallengeIndex(created.current_challenge_index ?? 0);
      setCompletedChallenges(normalizeCompletedChallenges(created.completed_challenges));
      setStepStatus("pending");
      setStatusMessage(
        `Sequence ready: ${normalizedSequence.map(challengeLabel).join(" -> ") || challengeLabel(created.challenge_type)}`,
      );
      setConnectionState("connecting");
      params.appendLog("pipeline", "Session created", created);

      const websocket = new WebSocket(`${wsBase}${created.ws_url}`);
      socketRef.current = websocket;

      websocket.onopen = () => {
        setConnectionState("open");
        params.appendLog("pipeline", "WebSocket open", { session_id: created.session_id });
        captureTimerRef.current = window.setInterval(() => {
          captureFrameRef.current(socketRef.current, {
            includeTrackedSignals: autoAssistRef.current,
            forceSpoof: forceSpoofRef.current,
          });
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
            autoAssistRef.current &&
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
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Session creation failed.";
      setStatusMessage(message);
      params.appendLog("pipeline", "Session creation failed", { message });
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
    sendFinalize,
  };
}

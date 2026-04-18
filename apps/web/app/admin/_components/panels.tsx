"use client";

import type { RefObject } from "react";
import type {
  ChallengeType,
  HealthResponse,
  StepStatus,
  VerificationDebugPayload,
  VerificationMode,
  VerificationResult,
} from "@sui-human/shared";
import {
  browserTuningDefaults,
  httpBase,
  sectionLabels,
  verificationModeHints,
  verificationModeLabels,
} from "../_lib/constants";
import type {
  AttackType,
  CalibrationLabel,
  CalibrationRecord,
  HarnessLogSection,
  LandmarkEngineState,
  LandmarkMetrics,
  LogEntry,
  ManualAction,
  SourceSplit,
} from "../_lib/types";
import { challengeHint, challengeLabel, formatMetric, formatPercent } from "../_lib/utils";

export function AdminHeroPanel(props: {
  cameraState: "idle" | "ready" | "error";
  landmarkState: LandmarkEngineState;
  connectionState: string;
  challengeType: ChallengeType | null;
  verificationMode: VerificationMode;
}) {
  return (
    <section className="panel hero-panel">
      <div>
        <p className="eyebrow">SUI HUMAN / ADMIN CONSOLE</p>
        <h1>Verifier testing and QA console</h1>
        <p className="lede">
          Internal console for threshold tuning, attack simulation, and verifier QA.
          Use the mode selector to run the backend in full, liveness-only, or
          anti-spoof-only finalize behavior.
        </p>
      </div>
      <div className="meta-grid">
        <div>
          <span>backend</span>
          <strong>{httpBase}</strong>
        </div>
        <div>
          <span>camera</span>
          <strong>{props.cameraState}</strong>
        </div>
        <div>
          <span>landmarks</span>
          <strong>{props.landmarkState}</strong>
        </div>
        <div>
          <span>websocket</span>
          <strong>{props.connectionState}</strong>
        </div>
        <div>
          <span>current step</span>
          <strong>{props.challengeType ? challengeLabel(props.challengeType) : "pending"}</strong>
        </div>
        <div>
          <span>qa mode</span>
          <strong>{verificationModeLabels[props.verificationMode]}</strong>
        </div>
      </div>
    </section>
  );
}

export function CameraPanel(props: {
  videoRef: RefObject<HTMLVideoElement | null>;
  overlayCanvasRef: RefObject<HTMLCanvasElement | null>;
  captureCanvasRef: RefObject<HTMLCanvasElement | null>;
  cameraMessage: string;
  landmarkMessage: string;
  landmarkMetrics: LandmarkMetrics;
  backendDebug: VerificationDebugPayload | null;
}) {
  return (
    <div className="panel camera-panel">
      <div className="panel-header">
        <h2>Webcam Overlay</h2>
        <p>{props.cameraMessage}</p>
      </div>
      <div className="video-shell">
        <video ref={props.videoRef} className="video" playsInline muted />
        <canvas ref={props.overlayCanvasRef} className="overlay-canvas" />
      </div>
      <canvas ref={props.captureCanvasRef} className="hidden-canvas" />
      <div className="telemetry-card">
        <div>
          <span>landmark engine</span>
          <strong>{props.landmarkMessage}</strong>
        </div>
        <div className="signal-grid">
          <div>
            <span>points</span>
            <strong>{props.landmarkMetrics.pointCount}</strong>
          </div>
          <div>
            <span>yaw</span>
            <strong>{props.landmarkMetrics.yaw ?? "n/a"}</strong>
          </div>
          <div>
            <span>pitch</span>
            <strong>{props.landmarkMetrics.pitch ?? "n/a"}</strong>
          </div>
          <div>
            <span>smile</span>
            <strong>{props.landmarkMetrics.smileRatio ?? "n/a"}</strong>
          </div>
          <div>
            <span>avg ear</span>
            <strong>{props.landmarkMetrics.averageEar ?? "n/a"}</strong>
          </div>
          <div>
            <span>backend face</span>
            <strong>{props.backendDebug?.face_detection?.detected ? "locked" : "searching"}</strong>
          </div>
          <div>
            <span>quality</span>
            <strong>
              {props.backendDebug?.quality?.passed
                ? "ok"
                : props.backendDebug?.quality?.primary_issue ?? "n/a"}
            </strong>
          </div>
        </div>
      </div>
    </div>
  );
}

export function SessionControlsPanel(props: {
  walletAddress: string;
  onWalletAddressChange: (value: string) => void;
  verificationMode: VerificationMode;
  onVerificationModeChange: (value: VerificationMode) => void;
  challengeType: ChallengeType | null;
  challengeSequence: ChallengeType[];
  completedChallenges: ChallengeType[];
  currentChallengeIndex: number;
  stepStatus: StepStatus;
  autoAssist: boolean;
  onAutoAssistChange: (value: boolean) => void;
  forceSpoof: boolean;
  onForceSpoofChange: (value: boolean) => void;
  busy: boolean;
  cameraState: "idle" | "ready" | "error";
  canFinalize: boolean;
  finalizeRequested: boolean;
  onStartSession: () => void;
  onFinalize: () => void;
  onQueueAction: (action: ManualAction) => void;
  statusMessage: string;
  progress: number;
  sessionId: string | null;
  resultMode: string;
}) {
  return (
    <div className="panel control-panel">
      <div className="panel-header">
        <h2>Session Controls</h2>
        <p>{challengeHint(props.challengeType)}</p>
      </div>

      <label className="field">
        <span>wallet address</span>
        <input
          value={props.walletAddress}
          onChange={(event) => props.onWalletAddressChange(event.target.value)}
        />
      </label>

      <label className="field">
        <span>qa mode</span>
        <select
          value={props.verificationMode}
          onChange={(event) => props.onVerificationModeChange(event.target.value as VerificationMode)}
        >
          <option value="full">full</option>
          <option value="liveness_only">liveness_only</option>
          <option value="antispoof_only">antispoof_only</option>
        </select>
        <small className="field-hint">{verificationModeHints[props.verificationMode]}</small>
      </label>

      <div className="sequence-card">
        <span>challenge sequence</span>
        <ol className="sequence-list">
          {props.challengeSequence.length === 0 ? (
            <li className="sequence-item is-upcoming">Start a session to load the sequence.</li>
          ) : (
            props.challengeSequence.map((step, index) => {
              const completed =
                props.completedChallenges.includes(step) &&
                index < props.currentChallengeIndex + 1;
              const current =
                index === props.currentChallengeIndex && props.stepStatus !== "completed";
              const className = completed
                ? "sequence-item is-completed"
                : current
                  ? "sequence-item is-current"
                  : props.stepStatus === "completed" && index === props.currentChallengeIndex
                    ? "sequence-item is-completed"
                    : "sequence-item is-upcoming";

              return (
                <li className={className} key={`${step}-${index}`}>
                  <strong>{index + 1}.</strong> {challengeLabel(step)}
                </li>
              );
            })
          )}
        </ol>
      </div>

      <div className="toggle-row">
        <label>
          <input
            checked={props.autoAssist}
            onChange={(event) => props.onAutoAssistChange(event.target.checked)}
            type="checkbox"
          />
          landmark assist
        </label>
        <label>
          <input
            checked={props.forceSpoof}
            onChange={(event) => props.onForceSpoofChange(event.target.checked)}
            type="checkbox"
          />
          force spoof
        </label>
      </div>

      <div className="button-row">
        <button disabled={props.busy || props.cameraState !== "ready"} onClick={props.onStartSession}>
          {props.busy ? "Starting..." : "Start session"}
        </button>
        <button disabled={!props.canFinalize} onClick={props.onFinalize} type="button">
          {props.finalizeRequested ? "Finalizing..." : "Finalize"}
        </button>
      </div>

      <div className="button-grid">
        <button onClick={() => props.onQueueAction("blink")} type="button">Trigger blink</button>
        <button onClick={() => props.onQueueAction("turn_left")} type="button">Trigger left</button>
        <button onClick={() => props.onQueueAction("turn_right")} type="button">Trigger right</button>
        <button onClick={() => props.onQueueAction("nod_head")} type="button">Trigger nod</button>
        <button onClick={() => props.onQueueAction("smile")} type="button">Trigger smile</button>
        <button onClick={() => props.onQueueAction("spoof")} type="button">Trigger spoof</button>
      </div>

      <div className="status-box">
        <div>
          <span>status</span>
          <strong>{props.statusMessage}</strong>
        </div>
        <div>
          <span>step status</span>
          <strong>{props.stepStatus}</strong>
        </div>
        <div>
          <span>progress</span>
          <strong>{Math.round(props.progress * 100)}%</strong>
        </div>
        <div>
          <span>session</span>
          <strong>{props.sessionId ?? "none"}</strong>
        </div>
        <div>
          <span>result mode</span>
          <strong>{props.resultMode}</strong>
        </div>
      </div>
    </div>
  );
}

export function BackendHealthPanel({ health }: { health: HealthResponse | null }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Backend Health</h2>
        <p>Quick view of the local verifier service.</p>
      </div>
      {health ? (
        <div className="status-box">
          <div><span>status</span><strong>{health.status}</strong></div>
          <div><span>redis</span><strong>{health.redis}</strong></div>
          <div><span>models</span><strong>{health.models}</strong></div>
          <div><span>chain</span><strong>{health.chain_adapter}</strong></div>
          <div><span>storage</span><strong>{health.storage_adapter}</strong></div>
          <div><span>encryption</span><strong>{health.encryption_adapter}</strong></div>
        </div>
      ) : (
        <p>Waiting for health response...</p>
      )}
    </div>
  );
}

export function ServerChecksPanel(props: {
  backendDebug: VerificationDebugPayload | null;
  result: VerificationResult | null;
}) {
  const serverQualityFeedback =
    props.backendDebug?.quality?.feedback && props.backendDebug.quality.feedback.length > 0
      ? props.backendDebug.quality.feedback.join(" | ")
      : "No quality guidance yet.";
  const serverAntiSpoofScore =
    props.result?.spoof_score ?? props.backendDebug?.antispoof?.spoof_score;
  const serverAntiSpoofMax =
    props.result?.max_spoof_score ??
    props.result?.spoof_score ??
    props.backendDebug?.antispoof?.max_spoof_score ??
    props.backendDebug?.antispoof?.spoof_score;
  const serverAntiSpoofMessage =
    props.backendDebug?.antispoof?.message ?? "No anti-spoof guidance yet.";
  const serverSpotcheckStatus = props.backendDebug?.landmark_spotcheck?.enforced
    ? props.backendDebug?.landmark_spotcheck?.passed
      ? "passed"
      : "blocked"
    : "not_enforced";
  const serverSpotcheckMismatch = props.backendDebug?.landmark_spotcheck?.mismatch_pixels;
  const serverSpotcheckThreshold = props.backendDebug?.landmark_spotcheck?.threshold_pixels;
  const serverSpotcheckMessage =
    props.backendDebug?.landmark_spotcheck?.message ?? "Landmark spot-check unavailable.";
  const serverFailureReason =
    props.result?.status === "failed"
      ? props.result.failure_reason ?? "unknown_failure"
      : props.result?.status === "verified"
        ? "none"
        : "No terminal verdict yet.";

  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Server Checks</h2>
        <p>Live backend decisions for face detection, quality, liveness, and the terminal verdict.</p>
      </div>
      <div className="status-box">
        <div><span>face gate</span><strong>{props.backendDebug?.face_detection?.detected ? "detected" : "missing"}</strong></div>
        <div><span>face confidence</span><strong>{formatMetric(props.backendDebug?.face_detection?.confidence)}</strong></div>
        <div><span>quality gate</span><strong>{props.backendDebug?.quality?.passed ? "passed" : "blocked"}</strong></div>
        <div><span>quality issue</span><strong>{props.backendDebug?.quality?.primary_issue ?? "none"}</strong></div>
        <div><span>quality score</span><strong>{formatMetric(props.backendDebug?.quality?.score)}</strong></div>
        <div><span>liveness step</span><strong>{props.backendDebug?.liveness?.current_step ? challengeLabel(props.backendDebug.liveness.current_step as ChallengeType) : "pending"}</strong></div>
        <div><span>step progress</span><strong>{formatPercent(props.backendDebug?.liveness?.step_progress)}</strong></div>
        <div><span>spot-check</span><strong>{serverSpotcheckStatus}</strong></div>
        <div><span>spot mismatch</span><strong>{formatMetric(serverSpotcheckMismatch)}</strong></div>
        <div><span>anti-spoof</span><strong>{formatMetric(serverAntiSpoofScore)}</strong></div>
        <div><span>anti-spoof max</span><strong>{formatMetric(serverAntiSpoofMax)}</strong></div>
        <div><span>terminal verdict</span><strong>{props.result?.status ?? "streaming"}</strong></div>
      </div>
      <div className="server-note"><span>quality feedback</span><strong>{serverQualityFeedback}</strong></div>
      <div className="server-note"><span>failure reason</span><strong>{serverFailureReason}</strong></div>
      <div className="server-note">
        <span>spot-check note</span>
        <strong>
          {serverSpotcheckMessage}
          {typeof serverSpotcheckThreshold === "number"
            ? ` (threshold ${serverSpotcheckThreshold.toFixed(2)} px)`
            : ""}
        </strong>
      </div>
      <div className="server-note">
        <span>anti-spoof note</span>
        <strong>
          {serverAntiSpoofMessage}
          {props.backendDebug?.antispoof?.preview ? " (live preview)" : ""}
        </strong>
      </div>
    </div>
  );
}

export function TuningSnapshotPanel(props: { backendTuning: HealthResponse["tuning"] | undefined }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Tuning Snapshot</h2>
        <p>Current browser assist defaults and backend liveness thresholds.</p>
      </div>
      <div className="tuning-grid">
        <div className="tuning-card">
          <span>browser assist</span>
          <pre className="json-block">{JSON.stringify(browserTuningDefaults, null, 2)}</pre>
        </div>
        <div className="tuning-card">
          <span>backend liveness</span>
          <pre className="json-block">
            {props.backendTuning
              ? JSON.stringify(props.backendTuning, null, 2)
              : "Waiting for health tuning..."}
          </pre>
        </div>
      </div>
    </div>
  );
}

export function JsonPanel(props: { title: string; description: string; value: unknown }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>{props.title}</h2>
        <p>{props.description}</p>
      </div>
      <pre className="json-block">
        {typeof props.value === "string" ? props.value : JSON.stringify(props.value, null, 2)}
      </pre>
    </div>
  );
}

export function CalibrationExportPanel(props: {
  calibrationLabel: CalibrationLabel;
  onCalibrationLabelChange: (value: CalibrationLabel) => void;
  attackType: AttackType;
  onAttackTypeChange: (value: AttackType) => void;
  sourceSplit: SourceSplit;
  onSourceSplitChange: (value: SourceSplit) => void;
  calibrationNotes: string;
  onCalibrationNotesChange: (value: string) => void;
  onCopy: () => void;
  onDownload: () => void;
  calibrationMessage: string;
  calibrationRecord: CalibrationRecord | null;
}) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h2>Calibration Export</h2>
        <p>Save completed sessions as NDJSON rows for threshold tuning and QA.</p>
      </div>

      <label className="field">
        <span>label</span>
        <select
          value={props.calibrationLabel}
          onChange={(event) => props.onCalibrationLabelChange(event.target.value as CalibrationLabel)}
        >
          <option value="human">human</option>
          <option value="spoof">spoof</option>
        </select>
      </label>

      <label className="field">
        <span>attack type</span>
        <select
          value={props.attackType}
          onChange={(event) => props.onAttackTypeChange(event.target.value as AttackType)}
        >
          <option value="bona_fide">bona_fide</option>
          <option value="print">print</option>
          <option value="screen_replay">screen_replay</option>
          <option value="prerecorded_video">prerecorded_video</option>
          <option value="virtual_camera">virtual_camera</option>
          <option value="ai_image">ai_image</option>
          <option value="ai_video">ai_video</option>
          <option value="face_swap_replay">face_swap_replay</option>
          <option value="unknown_spoof">unknown_spoof</option>
        </select>
      </label>

      <label className="field">
        <span>source split</span>
        <select
          value={props.sourceSplit}
          onChange={(event) => props.onSourceSplitChange(event.target.value as SourceSplit)}
        >
          <option value="train_calibration">train_calibration</option>
          <option value="dev">dev</option>
          <option value="holdout">holdout</option>
        </select>
      </label>

      <label className="field">
        <span>notes</span>
        <textarea
          value={props.calibrationNotes}
          onChange={(event) => props.onCalibrationNotesChange(event.target.value)}
          placeholder="lighting, webcam, attack type, environment"
        />
      </label>

      <div className="button-row">
        <button onClick={props.onCopy} type="button">Copy NDJSON row</button>
        <button onClick={props.onDownload} type="button">Download NDJSON row</button>
      </div>

      <div className="status-box">
        <div><span>export status</span><strong>{props.calibrationMessage}</strong></div>
        <div><span>strategy</span><strong>pretrained + calibration</strong></div>
      </div>

      <pre className="json-block">
        {props.calibrationRecord
          ? JSON.stringify(props.calibrationRecord, null, 2)
          : "Complete a session to preview a calibration row."}
      </pre>
    </div>
  );
}

export function LogPanels(props: { logs: Record<HarnessLogSection, LogEntry[]> }) {
  return (
    <section className="grid">
      {(["pipeline", "detection", "signals"] as const).map((section) => (
        <div className="panel" key={section}>
          <div className="panel-header">
            <h2>{sectionLabels[section]}</h2>
            <p>Newest 20 entries. Summary first, raw JSON underneath.</p>
          </div>
          <ul className="log-list">
            {props.logs[section].length === 0 ? (
              <li>
                <strong>No entries yet.</strong>
                <span>Start a session to populate this panel.</span>
              </li>
            ) : (
              props.logs[section].map((entry) => (
                <li key={entry.id}>
                  <strong>{entry.summary}</strong>
                  <details className="log-details">
                    <summary>Raw JSON</summary>
                    <pre className="log-json">{entry.detail}</pre>
                  </details>
                </li>
              ))
            )}
          </ul>
        </div>
      ))}
    </section>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import type { ChallengeType, VerificationMode } from "@sui-human/shared";
import {
  AdminHeroPanel,
  BackendHealthPanel,
  CalibrationExportPanel,
  CameraPanel,
  JsonPanel,
  LogPanels,
  ServerChecksPanel,
  SessionControlsPanel,
  TuningSnapshotPanel,
} from "./_components/panels";
import { useCalibrationExport } from "./_hooks/use-calibration-export";
import { useCameraLandmarks } from "./_hooks/use-camera-landmarks";
import { useHarnessLogs } from "./_hooks/use-harness-logs";
import { useSessionMetricSummary } from "./_hooks/use-session-metric-summary";
import { useVerifierSession } from "./_hooks/use-verifier-session";
import { drawOverlay } from "./_lib/landmarks";
import type {
  AttackType,
  ChallengeSequenceMode,
  LandmarkMetrics,
} from "./_lib/types";

export default function AdminPage() {
  const [walletAddress, setWalletAddress] = useState("0xtesthuman");
  const [verificationMode, setVerificationMode] = useState<VerificationMode>("full");
  const [sequenceMode, setSequenceMode] = useState<ChallengeSequenceMode>("fixed");
  const [fixedSequenceLength, setFixedSequenceLength] = useState(2);
  const [fixedChallengeSequence, setFixedChallengeSequence] = useState<ChallengeType[]>([
    "turn_left",
    "open_mouth",
    "smile",
  ]);
  const [autoAssist, setAutoAssist] = useState(false);
  const [forceSpoof, setForceSpoof] = useState(false);

  const { logs, appendLog, appendDebugLogs, resetLogs } = useHarnessLogs();
  const { summary: sessionMetricSummary, updateSummary, resetSummary } =
    useSessionMetricSummary();
  const shouldTrackMetricsRef = useRef(false);

  const media = useCameraLandmarks({
    appendLog,
    onMetrics: (metrics: LandmarkMetrics) => {
      if (shouldTrackMetricsRef.current) {
        updateSummary(metrics);
      }
    },
  });

  const verifier = useVerifierSession({
    walletAddress,
    verificationMode,
    challengeSequenceOverride:
      sequenceMode === "fixed"
        ? fixedChallengeSequence.slice(0, fixedSequenceLength)
        : null,
    autoAssist,
    appendLog,
    appendDebugLogs,
    resetLogs,
    resetSummary,
    captureFrame: media.captureFrame,
    resetCaptureState: media.resetCaptureState,
    forceSpoof,
  });

  const calibration = useCalibrationExport({
    sessionId: verifier.session?.session_id ?? null,
    verificationMode,
    challengeType: verifier.challengeType,
    challengeSequence: verifier.challengeSequence,
    progress: verifier.progress,
    result: verifier.result,
    sessionMetricSummary,
    appendLog,
  });

  useEffect(() => {
    shouldTrackMetricsRef.current = Boolean(verifier.session && !verifier.result);
  }, [verifier.session, verifier.result]);

  useEffect(() => {
    drawOverlay({
      video: media.videoRef.current,
      canvas: media.overlayCanvasRef.current,
      face: media.latestFaceRef.current,
      metrics: media.landmarkMetrics,
      debug: verifier.backendDebug,
      stepStatus: verifier.stepStatus,
    });
  }, [media.landmarkMetrics, verifier.backendDebug, verifier.stepStatus]);

  const canFinalize = Boolean(verifier.session) && !verifier.finalizeRequested && !verifier.result;

  return (
    <main className="page-shell">
      <AdminHeroPanel
        cameraState={media.cameraState}
        landmarkState={media.landmarkState}
        connectionState={verifier.connectionState}
        challengeType={verifier.challengeType}
        verificationMode={verificationMode}
      />

      <section className="grid">
        <CameraPanel
          videoRef={media.videoRef}
          overlayCanvasRef={media.overlayCanvasRef}
          captureCanvasRef={media.captureCanvasRef}
          cameraMessage={media.cameraMessage}
          landmarkMessage={media.landmarkMessage}
          landmarkMetrics={media.landmarkMetrics}
          backendDebug={verifier.backendDebug}
        />

        <SessionControlsPanel
          walletAddress={walletAddress}
          onWalletAddressChange={setWalletAddress}
          verificationMode={verificationMode}
          onVerificationModeChange={setVerificationMode}
          sequenceMode={sequenceMode}
          onSequenceModeChange={setSequenceMode}
          fixedSequenceLength={fixedSequenceLength}
          onFixedSequenceLengthChange={setFixedSequenceLength}
          fixedChallengeSequence={fixedChallengeSequence}
          onFixedChallengeSequenceChange={setFixedChallengeSequence}
          challengeType={verifier.challengeType}
          challengeSequence={verifier.challengeSequence}
          completedChallenges={verifier.completedChallenges}
          currentChallengeIndex={verifier.currentChallengeIndex}
          stepStatus={verifier.stepStatus}
          autoAssist={autoAssist}
          onAutoAssistChange={setAutoAssist}
          forceSpoof={forceSpoof}
          onForceSpoofChange={setForceSpoof}
          busy={verifier.busy}
          cameraState={media.cameraState}
          canFinalize={canFinalize}
          finalizeRequested={verifier.finalizeRequested}
          onStartSession={() => {
            calibration.resetCalibrationExport();
            void verifier.startSession();
          }}
          onFinalize={verifier.sendFinalize}
          onQueueAction={media.queueManualAction}
          statusMessage={verifier.statusMessage}
          progress={verifier.progress}
          sessionId={verifier.session?.session_id ?? null}
          resultMode={verifier.result?.evaluation_mode ?? verificationMode}
        />
      </section>

      <section className="grid">
        <BackendHealthPanel health={verifier.health} />
        <ServerChecksPanel
          backendDebug={verifier.backendDebug}
          result={verifier.result}
          reportedAttackType={calibration.attackType}
        />
        <TuningSnapshotPanel backendTuning={verifier.health?.tuning} />
        <JsonPanel
          title="Landmark Telemetry"
          description="Latest browser-side metrics and the backend debug payload."
          value={{ browser: media.landmarkMetrics, backend: verifier.backendDebug }}
        />
      </section>

      <section className="grid">
        <JsonPanel
          title="Latest Result"
          description="Terminal event from the verifier."
          value={verifier.result ?? "No terminal result yet."}
        />
        <CalibrationExportPanel
          calibrationLabel={calibration.calibrationLabel}
          onCalibrationLabelChange={(nextLabel) => {
            calibration.setCalibrationLabel(nextLabel);
            calibration.setAttackType(
              (nextLabel === "human" ? "bona_fide" : "unknown_spoof") as AttackType,
            );
          }}
          attackType={calibration.attackType}
          onAttackTypeChange={calibration.setAttackType}
          sourceSplit={calibration.sourceSplit}
          onSourceSplitChange={calibration.setSourceSplit}
          calibrationNotes={calibration.calibrationNotes}
          onCalibrationNotesChange={calibration.setCalibrationNotes}
          onCopy={() => void calibration.copyCalibrationRow()}
          onDownload={calibration.downloadCalibrationRow}
          calibrationMessage={calibration.calibrationMessage}
          calibrationRecord={calibration.calibrationRecord}
        />
      </section>

      <LogPanels logs={logs} />
    </main>
  );
}

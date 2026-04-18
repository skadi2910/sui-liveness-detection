"use client";

import { useEffect, useRef, useState } from "react";
import type {
  ChallengeType,
  VerificationMode,
  VerificationResult,
} from "@sui-human/shared";
import { httpBase } from "../_lib/constants";
import type {
  AttackType,
  CalibrationLabel,
  CalibrationRecord,
  SessionMetricSummary,
  SourceSplit,
} from "../_lib/types";
import { buildCalibrationRecord, deriveAttackTypeForLabel, normalizeChallengeSequence } from "../_lib/utils";

type AppendLog = (section: "pipeline" | "detection" | "signals", summary: string, detail?: unknown) => void;

export function useCalibrationExport(params: {
  sessionId: string | null;
  verificationMode: VerificationMode;
  challengeType: ChallengeType | null;
  challengeSequence: ChallengeType[];
  progress: number;
  result: VerificationResult | null;
  sessionMetricSummary: SessionMetricSummary;
  appendLog: AppendLog;
}) {
  const [calibrationLabel, setCalibrationLabel] = useState<CalibrationLabel>("human");
  const [attackType, setAttackType] = useState<AttackType>("bona_fide");
  const [sourceSplit, setSourceSplit] = useState<SourceSplit>("train_calibration");
  const [calibrationNotes, setCalibrationNotes] = useState("");
  const [calibrationMessage, setCalibrationMessage] = useState(
    "Complete a session to export a calibration row.",
  );
  const lastAutoSavedSessionIdRef = useRef<string | null>(null);

  function buildRecord(
    terminalResult: VerificationResult | null = params.result,
    terminalChallengeType: ChallengeType | null = params.challengeType,
    terminalChallengeSequence: ChallengeType[] = params.challengeSequence,
    terminalProgress: number = params.progress,
    label: CalibrationLabel = calibrationLabel,
  ): CalibrationRecord | null {
    return buildCalibrationRecord({
      sessionId: params.sessionId,
      verificationMode: params.verificationMode,
      label,
      attackType,
      sourceSplit,
      challengeType: terminalChallengeType,
      challengeSequence: terminalChallengeSequence,
      result: terminalResult
        ? {
            session_id: terminalResult.session_id,
            evaluation_mode: terminalResult.evaluation_mode,
            failure_reason: terminalResult.failure_reason,
            status: terminalResult.status,
            human: terminalResult.human,
            spoof_score: terminalResult.spoof_score,
            max_spoof_score: terminalResult.max_spoof_score,
            confidence: terminalResult.confidence,
          }
        : null,
      progress: terminalProgress,
      summary: params.sessionMetricSummary,
      notes: calibrationNotes,
    });
  }

  async function autoSaveSessionRecords(record: CalibrationRecord | null) {
    if (!record) {
      setCalibrationMessage("No completed session available to auto-save.");
      return;
    }

    const endpoints = [
      { key: "calibration", url: `${httpBase}/api/calibration/append` },
      { key: "attack_matrix", url: `${httpBase}/api/attack-matrix/append` },
    ] as const;

    const results = await Promise.allSettled(
      endpoints.map(async (endpoint) => {
        const response = await fetch(endpoint.url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ record }),
        });

        if (!response.ok) {
          const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
          throw new Error(payload.detail ?? `Could not auto-save ${endpoint.key} row.`);
        }

        const payload = (await response.json()) as {
          saved: boolean;
          sample_id?: string;
          output_path: string;
        };
        params.appendLog("pipeline", `${endpoint.key} row auto-saved`, payload);
        return payload.output_path;
      }),
    );

    const successes = results.filter(
      (item): item is PromiseFulfilledResult<string> => item.status === "fulfilled",
    );
    const failures = results.filter((item) => item.status === "rejected");

    if (successes.length === endpoints.length) {
      setCalibrationMessage(
        `Rows auto-saved to ${successes.map((item) => item.value).join(" and ")}.`,
      );
      return;
    }

    const messages = failures.map((item) =>
      item.status === "rejected" && item.reason instanceof Error
        ? item.reason.message
        : "Unknown auto-save error.",
    );
    setCalibrationMessage(messages.join(" | "));
    params.appendLog("pipeline", "Auto-save failed", { messages, record });
  }

  async function copyCalibrationRow() {
    const record = buildRecord();
    if (!record) {
      setCalibrationMessage("No completed session available to export.");
      return;
    }

    try {
      await navigator.clipboard.writeText(`${JSON.stringify(record)}\n`);
      setCalibrationMessage("Calibration NDJSON row copied to clipboard.");
      params.appendLog("pipeline", "Calibration row copied", record);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not copy calibration row.";
      setCalibrationMessage(message);
      params.appendLog("pipeline", "Calibration copy failed", { message });
    }
  }

  function downloadCalibrationRow() {
    const record = buildRecord();
    if (!record) {
      setCalibrationMessage("No completed session available to export.");
      return;
    }

    const blob = new Blob([`${JSON.stringify(record)}\n`], {
      type: "application/x-ndjson;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${record.sample_id}.ndjson`;
    anchor.click();
    URL.revokeObjectURL(url);

    setCalibrationMessage("Calibration NDJSON row downloaded.");
    params.appendLog("pipeline", "Calibration row downloaded", record);
  }

  function resetCalibrationExport() {
    lastAutoSavedSessionIdRef.current = null;
    setCalibrationMessage("Complete a session to export a calibration row.");
  }

  useEffect(() => {
    if (!params.result || !params.sessionId) return;
    if (lastAutoSavedSessionIdRef.current === params.result.session_id) return;

    const terminalLabel: CalibrationLabel = params.result.human ? "human" : "spoof";
    const terminalAttackType = deriveAttackTypeForLabel(terminalLabel, attackType);
    const terminalRecord = buildRecord(
      params.result,
      params.result.challenge_type,
      normalizeChallengeSequence(
        params.result.challenge_sequence,
        params.result.challenge_type,
      ),
      params.result.status === "verified" ? 1 : params.progress,
      terminalLabel,
    );

    setCalibrationLabel(terminalLabel);
    setAttackType(terminalAttackType as AttackType);
    lastAutoSavedSessionIdRef.current = params.result.session_id;
    void autoSaveSessionRecords(
      terminalRecord ? { ...terminalRecord, attack_type: terminalAttackType } : null,
    );
  }, [
    attackType,
    params.challengeSequence,
    params.challengeType,
    params.progress,
    params.result,
    params.sessionId,
    params.sessionMetricSummary,
    sourceSplit,
    calibrationNotes,
  ]);

  return {
    calibrationLabel,
    setCalibrationLabel,
    attackType,
    setAttackType,
    sourceSplit,
    setSourceSplit,
    calibrationNotes,
    setCalibrationNotes,
    calibrationMessage,
    calibrationRecord: buildRecord(),
    copyCalibrationRow,
    downloadCalibrationRow,
    resetCalibrationExport,
  };
}

"use client";

import { startTransition, useCallback, useRef, useState } from "react";
import type { VerificationDebugPayload } from "@sui-human/shared";
import { maxLogEntries } from "../_lib/constants";
import type { HarnessLogSection, LogEntry } from "../_lib/types";
import { emptyLogs, formatMetric, nextId } from "../_lib/utils";

export function useHarnessLogs() {
  const [logs, setLogs] = useState<Record<HarnessLogSection, LogEntry[]>>(emptyLogs);
  const lastDebugSummariesRef = useRef<{ detection: string | null; signals: string | null }>({
    detection: null,
    signals: null,
  });

  const appendLog = useCallback((
    section: HarnessLogSection,
    summary: string,
    detail: unknown = summary,
  ) => {
    const entry: LogEntry = {
      id: nextId(),
      summary,
      detail: typeof detail === "string" ? detail : JSON.stringify(detail, null, 2),
    };
    startTransition(() => {
      setLogs((current) => ({
        ...current,
        [section]: [entry, ...current[section]].slice(0, maxLogEntries),
      }));
    });
  }, []);

  const appendDebugLogs = useCallback((debug: VerificationDebugPayload) => {
    const detectionSummary = `Face ${debug.face_detection?.detected ? "detected" : "missing"} / quality ${debug.quality?.passed ? "ok" : "check"} / landmarks ${debug.landmarks?.point_count ?? 0}`;
    if (lastDebugSummariesRef.current.detection !== detectionSummary) {
      lastDebugSummariesRef.current.detection = detectionSummary;
      appendLog("detection", detectionSummary, debug);
    }

    const signalSummary = [
      `EAR ${formatMetric(debug.landmarks?.average_ear)}`,
      `yaw ${formatMetric(debug.landmarks?.yaw)}`,
      `pitch ${formatMetric(debug.landmarks?.pitch)}`,
      `smile ${formatMetric(debug.landmarks?.smile_ratio)}`,
      `quality ${formatMetric(debug.quality?.score)}`,
      `spotcheck ${debug.landmark_spotcheck?.passed === false ? "fail" : "ok"}`,
      `spoof ${formatMetric(debug.antispoof?.spoof_score)}`,
    ].join(" | ");
    if (lastDebugSummariesRef.current.signals !== signalSummary) {
      lastDebugSummariesRef.current.signals = signalSummary;
      appendLog("signals", signalSummary, debug);
    }
  }, [appendLog]);

  const resetLogs = useCallback(() => {
    setLogs(emptyLogs());
    lastDebugSummariesRef.current = { detection: null, signals: null };
  }, []);

  return { logs, appendLog, appendDebugLogs, resetLogs };
}

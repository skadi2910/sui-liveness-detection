"use client";

import { useState } from "react";
import type { LandmarkMetrics, SessionMetricSummary } from "../_lib/types";
import {
  emptySessionMetricSummary,
  maxNullable,
  minNullable,
} from "../_lib/utils";

export function useSessionMetricSummary() {
  const [summary, setSummary] = useState<SessionMetricSummary>(emptySessionMetricSummary);

  function updateSummary(metrics: LandmarkMetrics) {
    if (!metrics.faceDetected) return;
    setSummary((current) => ({
      landmarksCaptured: current.landmarksCaptured + 1,
      pointCountMax: Math.max(current.pointCountMax, metrics.pointCount),
      yawMin: minNullable(current.yawMin, metrics.yaw),
      yawMax: maxNullable(current.yawMax, metrics.yaw),
      yawAbsPeak: maxNullable(
        current.yawAbsPeak,
        metrics.yaw === null ? null : Math.abs(metrics.yaw),
      ),
      pitchMin: minNullable(current.pitchMin, metrics.pitch),
      pitchMax: maxNullable(current.pitchMax, metrics.pitch),
      smileRatioMax: maxNullable(current.smileRatioMax, metrics.smileRatio),
      mouthRatioMax: maxNullable(current.mouthRatioMax, metrics.mouthRatio),
      earMin: minNullable(current.earMin, metrics.averageEar),
      earMax: maxNullable(current.earMax, metrics.averageEar),
      leftEarMin: minNullable(current.leftEarMin, metrics.leftEar),
      rightEarMin: minNullable(current.rightEarMin, metrics.rightEar),
    }));
  }

  function resetSummary() {
    setSummary(emptySessionMetricSummary());
  }

  return { summary, setSummary, updateSummary, resetSummary };
}

"use client";

import { useRef, useState } from "react";
import { useCameraLandmarks as useBaseCameraLandmarks } from "../../../features/verifier-core/hooks/use-camera-landmarks";
import { actionMetadata, nextPitchMetadata } from "../_lib/camera-harness";
import type { LandmarkMetrics, ManualAction } from "../_lib/types";

type AppendLog = (section: "pipeline" | "detection" | "signals", summary: string, detail?: unknown) => void;

export function useCameraLandmarks(params: {
  appendLog: AppendLog;
  onMetrics: (metrics: LandmarkMetrics) => void;
}) {
  const base = useBaseCameraLandmarks(params);
  const queuedActionsRef = useRef<ManualAction[]>([]);
  const pendingPitchValuesRef = useRef<number[]>([]);
  const [queuedActions, setQueuedActions] = useState<ManualAction[]>([]);

  function queueManualAction(action: ManualAction) {
    queuedActionsRef.current = [...queuedActionsRef.current, action];
    setQueuedActions(queuedActionsRef.current);
  }

  function consumeManualAction(): ManualAction | null {
    const [selected, ...rest] = queuedActionsRef.current;
    queuedActionsRef.current = rest;
    setQueuedActions(rest);
    return selected ?? null;
  }

  function captureFrame(
    socket: WebSocket | null,
    options: { includeTrackedSignals: boolean; forceSpoof: boolean },
  ) {
    const action = consumeManualAction();

    if (action === "nod_head") {
      pendingPitchValuesRef.current.push(14, -14);
    }

    const extraMetadata = {
      ...actionMetadata(action),
      ...nextPitchMetadata(pendingPitchValuesRef.current),
      ...(options.forceSpoof ? { presentation_attack: true } : {}),
    };

    base.captureFrame(socket, {
      includeTrackedSignals: options.includeTrackedSignals,
      extraMetadata,
    });

    if (action) {
      params.appendLog("pipeline", `Manual action queued: ${action.replace("_", " ")}`, extraMetadata);
    }
  }

  function resetCaptureState() {
    queuedActionsRef.current = [];
    pendingPitchValuesRef.current = [];
    setQueuedActions([]);
    base.resetCaptureState();
  }

  return {
    ...base,
    queuedActions,
    queueManualAction,
    captureFrame,
    resetCaptureState,
  };
}

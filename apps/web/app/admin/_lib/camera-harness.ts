"use client";

import type { ManualAction } from "./types";

export function actionMetadata(action: ManualAction | null) {
  if (action === "open_mouth") return { mouth_open: true, mouth_ratio: 0.38 };
  if (action === "turn_left") return { head_turn: "left" as const };
  if (action === "turn_right") return { head_turn: "right" as const };
  if (action === "smile") return { smile: true, smile_ratio: 0.48 };
  if (action === "spoof") return { presentation_attack: true };
  return {};
}

export function nextPitchMetadata(pendingPitchValues: number[]) {
  const pitch = pendingPitchValues.shift();
  if (typeof pitch !== "number") return {};

  return {
    pitch,
    pitch_ratio: Math.round((pitch / 180) * 10000) / 10000,
  };
}

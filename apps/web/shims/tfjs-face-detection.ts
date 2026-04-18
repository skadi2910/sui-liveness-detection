"use client";

import type { MediaPipeFaceDetectorTfjsModelConfig } from "@tensorflow-models/face-detection/dist/tfjs/types";
import type { FaceDetector } from "@tensorflow-models/face-detection/dist/face_detector";

export enum SupportedModels {
  MediaPipeFaceDetector = "MediaPipeFaceDetector",
}

export async function createDetector(
  model: SupportedModels,
  modelConfig: MediaPipeFaceDetectorTfjsModelConfig,
): Promise<FaceDetector> {
  if (model !== SupportedModels.MediaPipeFaceDetector) {
    throw new Error(`${model} is not a supported model name.`);
  }

  const detectorModule = await import("@tensorflow-models/face-detection/dist/tfjs/detector");
  return detectorModule.load(modelConfig);
}

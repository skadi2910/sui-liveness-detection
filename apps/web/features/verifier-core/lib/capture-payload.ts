export type CapturePayloadMetadataArgs = {
  extraMetadata?: Record<string, unknown>;
  frameNumber: number;
  width: number;
  height: number;
};

export type LandmarkPayloadMetadataArgs = CapturePayloadMetadataArgs & {
  packetMetadata?: Record<string, unknown>;
  trackedSignalMetadata?: Record<string, unknown>;
};

export function buildFrameEventMetadata(
  args: CapturePayloadMetadataArgs,
): Record<string, unknown> {
  return {
    ...(args.extraMetadata ?? {}),
    frame_number: args.frameNumber,
    frame_width: args.width,
    frame_height: args.height,
  };
}

export function buildLandmarkEventMetadata(
  args: LandmarkPayloadMetadataArgs,
): Record<string, unknown> {
  return {
    ...(args.packetMetadata ?? {}),
    ...(args.trackedSignalMetadata ?? {}),
    ...(args.extraMetadata ?? {}),
    frame_number: args.frameNumber,
    frame_width: args.width,
    frame_height: args.height,
  };
}

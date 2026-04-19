import { describe, expect, it } from "vitest";

import {
  buildFrameEventMetadata,
  buildLandmarkEventMetadata,
} from "./capture-payload";

describe("capture payload metadata", () => {
  it("keeps tracked signals out of raw frame events", () => {
    const metadata = buildFrameEventMetadata({
      extraMetadata: { session_phase: "verify" },
      frameNumber: 7,
      width: 640,
      height: 480,
    });

    expect(metadata).toEqual({
      session_phase: "verify",
      frame_number: 7,
      frame_width: 640,
      frame_height: 480,
    });
    expect(metadata).not.toHaveProperty("smile");
    expect(metadata).not.toHaveProperty("head_turn");
    expect(metadata).not.toHaveProperty("pitch");
  });

  it("attaches tracked landmark signals only to landmark events", () => {
    const metadata = buildLandmarkEventMetadata({
      packetMetadata: { smile_ratio: 0.62, yaw: 18.1 },
      trackedSignalMetadata: { smile: true, head_turn: "right", pitch: 14 },
      extraMetadata: { session_phase: "verify" },
      frameNumber: 8,
      width: 640,
      height: 480,
    });

    expect(metadata).toEqual({
      smile_ratio: 0.62,
      yaw: 18.1,
      smile: true,
      head_turn: "right",
      pitch: 14,
      session_phase: "verify",
      frame_number: 8,
      frame_width: 640,
      frame_height: 480,
    });
  });
});

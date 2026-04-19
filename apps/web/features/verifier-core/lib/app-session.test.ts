import { describe, expect, it } from "vitest";
import type { SessionRecordResponse } from "@sui-human/shared";
import {
  createBrowserSession,
  deriveAppRouteTarget,
  describeAppSession,
} from "./app-session";

function buildSession(
  overrides?: Partial<SessionRecordResponse>,
): SessionRecordResponse {
  return {
    session_id: "sess_demo",
    status: "created",
    challenge_type: "smile",
    challenge_sequence: ["smile", "nod_head"],
    current_challenge_index: 0,
    total_challenges: 2,
    completed_challenges: [],
    created_at: new Date().toISOString(),
    expires_at: new Date().toISOString(),
    ...overrides,
  };
}

describe("deriveAppRouteTarget", () => {
  it("routes active sessions back into verify", () => {
    expect(deriveAppRouteTarget(buildSession())).toEqual({
      kind: "verify",
      href: "/verify/sess_demo",
    });
  });

  it("routes terminal sessions into result", () => {
    expect(
      deriveAppRouteTarget(
        buildSession({
          status: "verified",
          result: {
            session_id: "sess_demo",
            status: "verified",
            evaluation_mode: "full",
            human: true,
            challenge_type: "smile",
            challenge_sequence: ["smile", "nod_head"],
            current_challenge_index: 1,
            total_challenges: 2,
            completed_challenges: ["smile", "nod_head"],
            confidence: 0.98,
            spoof_score: 0.02,
          },
        }),
      ),
    ).toEqual({
      kind: "result",
      href: "/result/sess_demo",
    });
  });

  it("keeps expired sessions on app restart flow", () => {
    expect(
      deriveAppRouteTarget(
        buildSession({
          status: "expired",
        }),
      ),
    ).toEqual({
      kind: "expired",
      href: "/result/sess_demo",
    });
  });
});

describe("describeAppSession", () => {
  it("describes missing sessions as ready for a fresh flow", () => {
    expect(describeAppSession(null).title).toContain("verify and mint");
  });

  it("describes active sessions as resumable", () => {
    expect(describeAppSession(buildSession()).title).toContain("Resume");
  });

  it("describes verified terminal sessions as ready", () => {
    expect(
      describeAppSession(
        buildSession({
          status: "verified",
          result: {
            session_id: "sess_demo",
            status: "verified",
            evaluation_mode: "full",
            human: true,
            challenge_type: "smile",
            challenge_sequence: ["smile", "nod_head"],
            current_challenge_index: 1,
            total_challenges: 2,
            completed_challenges: ["smile", "nod_head"],
            confidence: 0.98,
            spoof_score: 0.02,
          },
        }),
      ).badge,
    ).toBe("Verified");
  });
});

describe("createBrowserSession", () => {
  it("requires a connected wallet address before creating a product session", async () => {
    await expect(
      createBrowserSession({ walletAddress: "" }),
    ).rejects.toThrow("Connect a Sui wallet before starting verification.");
  });
});

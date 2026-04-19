import { describe, expect, it } from "vitest";
import { deriveOwnerDecryptPanelStatus } from "./panel-state";

describe("deriveOwnerDecryptPanelStatus", () => {
  it("shows wallet disconnected before any proof work starts", () => {
    expect(
      deriveOwnerDecryptPanelStatus({
        isWalletConnected: false,
        proofLoadState: "idle",
        decryptState: "idle",
      }),
    ).toBe("wallet_disconnected");
  });

  it("shows proof ready once a proof is loaded and decrypt has not started", () => {
    expect(
      deriveOwnerDecryptPanelStatus({
        isWalletConnected: true,
        proofLoadState: "ready",
        decryptState: "idle",
      }),
    ).toBe("proof_ready");
  });

  it("shows awaiting wallet approval while signature approval is pending", () => {
    expect(
      deriveOwnerDecryptPanelStatus({
        isWalletConnected: true,
        proofLoadState: "ready",
        decryptState: "awaiting_wallet_approval",
      }),
    ).toBe("awaiting_wallet_approval");
  });

  it("shows decrypted after successful owner-side evidence access", () => {
    expect(
      deriveOwnerDecryptPanelStatus({
        isWalletConnected: true,
        proofLoadState: "ready",
        decryptState: "success",
      }),
    ).toBe("decrypted");
  });

  it("shows decrypt failed after a failed retryable owner decrypt attempt", () => {
    expect(
      deriveOwnerDecryptPanelStatus({
        isWalletConnected: true,
        proofLoadState: "ready",
        decryptState: "error",
      }),
    ).toBe("decrypt_failed");
  });
});

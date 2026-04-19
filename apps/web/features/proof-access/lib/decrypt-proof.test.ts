import { describe, expect, it, vi } from "vitest";
import { decryptOwnedProofEvidence } from "./decrypt-proof";

describe("decryptOwnedProofEvidence", () => {
  it("signs the session key, fetches Walrus bytes, and decrypts evidence", async () => {
    const signPersonalMessage = vi.fn().mockResolvedValue({ signature: "signed-personal-message" });
    const setPersonalMessageSignature = vi.fn().mockResolvedValue(undefined);
    const sessionKey = {
      getPersonalMessage: () => new TextEncoder().encode("please sign"),
      setPersonalMessageSignature,
    };
    const createSessionKey = vi.fn().mockResolvedValue(sessionKey);
    const buildApprovalTx = vi.fn().mockResolvedValue(new Uint8Array([8, 9, 10]));
    const decrypt = vi.fn().mockResolvedValue(
      new TextEncoder().encode(
        JSON.stringify({
          evidence_schema_version: 1,
          session_id: "sess_owner",
          wallet_address: "0xwallet",
          challenge_type: "smile",
          challenge_sequence: ["smile", "nod_head"],
          session_started_at: "2026-04-19T10:00:00.000Z",
          session_completed_at: "2026-04-19T10:01:00.000Z",
          frame_hashes: ["sha256:frame-a"],
          landmark_snapshot: {},
          spoof_score_summary: {},
          model_hashes: { verifier_bundle: "sha256:bundle" },
          captured_at: "2026-04-19T10:01:00.000Z",
        }),
      ),
    );
    const createSealClient = vi.fn().mockReturnValue({ decrypt });
    const fetchFn = vi.fn().mockResolvedValue({
      ok: true,
      arrayBuffer: async () => Uint8Array.from([1, 2, 3]).buffer,
    });

    const result = await decryptOwnedProofEvidence({
      client: {} as never,
      dAppKit: { signPersonalMessage },
      config: {
        packageId: "0xpackage",
        network: "testnet",
        fullnodeUrl: "https://fullnode.testnet.sui.io:443",
        walrusAggregatorUrl: "https://aggregator.walrus-testnet.walrus.space",
        sealServerConfigs: [{ objectId: "0xserver", weight: 1 }],
        sealThreshold: 1,
        verifyKeyServers: false,
        sessionKeyTtlMinutes: 10,
        proofType: "0xpackage::proof_of_human::ProofOfHuman",
        missing: [],
      },
      ownerAddress: "0xwallet",
      proof: {
        proofId: "0xproof",
        owner: "0xwallet",
        walrusBlobId: "blob-live",
        walrusBlobObjectId: "0xblob",
        sealIdentity: "0xfdee80a78889bc2fa0f4433e99d50f86a7917aedd121419bab939358bca1b235",
        evidenceSchemaVersion: 1,
        modelHash: "sha256:model_bundle",
        confidenceBps: 9815,
        issuedAtMs: 1776568166926,
        expiresAtMs: 1784344166926,
        challengeType: "smile",
        transactionDigest: "0xtx",
      },
      fetchFn: fetchFn as never,
      createSealClient,
      createSessionKey: createSessionKey as never,
      buildApprovalTx: buildApprovalTx as never,
    });

    expect(createSessionKey).toHaveBeenCalledWith({
      address: "0xwallet",
      packageId: "0xpackage",
      ttlMin: 10,
      suiClient: {},
    });
    expect(signPersonalMessage).toHaveBeenCalledWith({
      message: new TextEncoder().encode("please sign"),
    });
    expect(setPersonalMessageSignature).toHaveBeenCalledWith("signed-personal-message");
    expect(buildApprovalTx).toHaveBeenCalledWith({
      client: {},
      packageId: "0xpackage",
      proof: expect.objectContaining({ proofId: "0xproof" }),
    });
    expect(fetchFn).toHaveBeenCalledWith(
      "https://aggregator.walrus-testnet.walrus.space/v1/blobs/blob-live",
    );
    expect(decrypt).toHaveBeenCalledWith({
      data: Uint8Array.from([1, 2, 3]),
      sessionKey,
      txBytes: new Uint8Array([8, 9, 10]),
    });
    expect(result.session_id).toBe("sess_owner");
  });
});


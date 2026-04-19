import { describe, expect, it } from "vitest";

import { deriveOwnedProofFromSession } from "./session-proof";

describe("deriveOwnedProofFromSession", () => {
  it("maps a minted verified session into dashboard proof metadata", () => {
    const proof = deriveOwnedProofFromSession(
      {
        session_id: "sess_1",
        status: "verified",
        challenge_type: "nod_head",
        challenge_sequence: ["turn_right", "open_mouth", "nod_head"],
        current_challenge_index: 2,
        total_challenges: 3,
        completed_challenges: ["turn_right", "open_mouth", "nod_head"],
        created_at: "2026-04-19T05:33:40.852078Z",
        expires_at: "2026-07-18T05:34:19.925696Z",
        result: {
          session_id: "sess_1",
          status: "verified",
          human: true,
          challenge_type: "nod_head",
          challenge_sequence: ["turn_right", "open_mouth", "nod_head"],
          current_challenge_index: 2,
          total_challenges: 3,
          completed_challenges: ["turn_right", "open_mouth", "nod_head"],
          confidence: 0.925,
          spoof_score: 0.0097,
          proof_id: "0xproof",
          transaction_digest: "0xtx",
          proof_operation: "renewed",
          chain_network: "sui-testnet",
          walrus_blob_id: "blob_123",
          walrus_blob_object_id: "0xblob",
          seal_identity: "0xseal",
          evidence_schema_version: 1,
          model_hash: "sha256:model",
          expires_at: "2026-07-18T05:34:19.925696Z",
        },
      },
      "0xwallet",
    );

    expect(proof).toEqual({
      proofId: "0xproof",
      owner: "0xwallet",
      walrusBlobId: "blob_123",
      walrusBlobObjectId: "0xblob",
      sealIdentity: "0xseal",
      evidenceSchemaVersion: 1,
      modelHash: "sha256:model",
      confidenceBps: 9250,
      issuedAtMs: Date.parse("2026-04-19T05:33:40.852078Z"),
      expiresAtMs: Date.parse("2026-07-18T05:34:19.925696Z"),
      challengeType: "nod_head",
      transactionDigest: "0xtx",
    });
  });
});

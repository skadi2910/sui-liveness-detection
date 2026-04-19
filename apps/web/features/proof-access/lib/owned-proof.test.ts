import { Buffer } from "node:buffer";
import { describe, expect, it } from "vitest";
import {
  decodeMoveStringField,
  decodeOwnedProofObject,
  selectLatestActiveProof,
} from "./owned-proof";

function encodeAscii(value: string) {
  return Buffer.from(value, "utf-8").toString("base64");
}

describe("decodeMoveStringField", () => {
  it("decodes base64 encoded vector<u8> strings into readable values", () => {
    expect(decodeMoveStringField(encodeAscii("smile"))).toBe("smile");
    expect(
      decodeMoveStringField(
        "MHhmZGVlODBhNzg4ODliYzJmYTBmNDQzM2U5OWQ1MGY4NmE3OTE3YWVkZDEyMTQxOWJhYjkzOTM1OGJjYTFiMjM1",
      ),
    ).toBe("0xfdee80a78889bc2fa0f4433e99d50f86a7917aedd121419bab939358bca1b235");
  });

  it("keeps already-readable values intact", () => {
    expect(decodeMoveStringField("0YDDxpDtQn1DB08Ai0PVtksuCOgxFR3yQ28xSxWBM1k")).toBe(
      "0YDDxpDtQn1DB08Ai0PVtksuCOgxFR3yQ28xSxWBM1k",
    );
  });
});

describe("decodeOwnedProofObject", () => {
  it("decodes proof metadata from Move json fields", () => {
    const decoded = decodeOwnedProofObject(
      {
        objectId: "0xproof",
        version: "1",
        digest: "digest",
        owner: { Address: "0xwallet" },
        type: "0xpackage::proof_of_human::ProofOfHuman",
        content: undefined,
        objectBcs: undefined,
        display: undefined,
        previousTransaction: "0xtx",
        json: {
          owner: "0xwallet",
          walrus_blob_id: "0YDDxpDtQn1DB08Ai0PVtksuCOgxFR3yQ28xSxWBM1k",
          walrus_blob_object_id: "0xde017d8287d43066965491ee0926f39fa0b482d9b7ded1ee8a4d6aa99fbaabcb",
          seal_identity:
            "MHhmZGVlODBhNzg4ODliYzJmYTBmNDQzM2U5OWQ1MGY4NmE3OTE3YWVkZDEyMTQxOWJhYjkzOTM1OGJjYTFiMjM1",
          evidence_schema_version: "1",
          model_hash: encodeAscii("sha256:model_bundle"),
          confidence_bps: "9815",
          issued_at_ms: "1776568166926",
          expires_at_ms: "1784344166926",
          challenge_type: encodeAscii("smile"),
        },
      },
      "0xwallet",
    );

    expect(decoded).toEqual({
      proofId: "0xproof",
      owner: "0xwallet",
      walrusBlobId: "0YDDxpDtQn1DB08Ai0PVtksuCOgxFR3yQ28xSxWBM1k",
      walrusBlobObjectId:
        "0xde017d8287d43066965491ee0926f39fa0b482d9b7ded1ee8a4d6aa99fbaabcb",
      sealIdentity:
        "0xfdee80a78889bc2fa0f4433e99d50f86a7917aedd121419bab939358bca1b235",
      evidenceSchemaVersion: 1,
      modelHash: "sha256:model_bundle",
      confidenceBps: 9815,
      issuedAtMs: 1776568166926,
      expiresAtMs: 1784344166926,
      challengeType: "smile",
      transactionDigest: "0xtx",
    });
  });
});

describe("selectLatestActiveProof", () => {
  it("ignores expired proofs and picks the latest active proof", () => {
    const proof = selectLatestActiveProof(
      [
        {
          proofId: "0xexpired",
          owner: "0xwallet",
          walrusBlobId: "expired",
          walrusBlobObjectId: "0xblob-expired",
          sealIdentity: "0xseal-expired",
          evidenceSchemaVersion: 1,
          modelHash: "sha256:expired",
          confidenceBps: 7001,
          issuedAtMs: 10,
          expiresAtMs: 100,
          challengeType: "smile",
        },
        {
          proofId: "0xolder-active",
          owner: "0xwallet",
          walrusBlobId: "older",
          walrusBlobObjectId: "0xblob-older",
          sealIdentity: "0xseal-older",
          evidenceSchemaVersion: 1,
          modelHash: "sha256:older",
          confidenceBps: 8000,
          issuedAtMs: 1000,
          expiresAtMs: 5000,
          challengeType: "smile",
        },
        {
          proofId: "0xlatest",
          owner: "0xwallet",
          walrusBlobId: "latest",
          walrusBlobObjectId: "0xblob-latest",
          sealIdentity: "0xseal-latest",
          evidenceSchemaVersion: 1,
          modelHash: "sha256:latest",
          confidenceBps: 9000,
          issuedAtMs: 2000,
          expiresAtMs: 9000,
          challengeType: "turn_left",
        },
      ],
      1000,
    );

    expect(proof?.proofId).toBe("0xlatest");
  });

  it("returns null when no active proofs remain", () => {
    expect(
      selectLatestActiveProof(
        [
          {
            proofId: "0xexpired",
            owner: "0xwallet",
            walrusBlobId: "expired",
            walrusBlobObjectId: "0xblob-expired",
            sealIdentity: "0xseal-expired",
            evidenceSchemaVersion: 1,
            modelHash: "sha256:expired",
            confidenceBps: 7001,
            issuedAtMs: 10,
            expiresAtMs: 100,
            challengeType: "smile",
          },
        ],
        1000,
      ),
    ).toBeNull();
  });
});


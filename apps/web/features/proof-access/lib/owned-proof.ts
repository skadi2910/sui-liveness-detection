import type { SuiClientTypes } from "@mysten/sui/client";
import type { OwnedProofMetadata } from "./types";

type OwnedProofObject = SuiClientTypes.Object<{
  json: true;
  previousTransaction: true;
}>;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function toNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim().length > 0) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function tryDecodeAsciiBase64(value: string) {
  try {
    const decoded =
      typeof atob === "function"
        ? new TextDecoder().decode(Uint8Array.from(atob(value), (char) => char.charCodeAt(0)))
        : Buffer.from(value, "base64").toString("utf-8");
    if (!decoded) {
      return null;
    }

    const printable = /^[\x20-\x7E\r\n\t]+$/.test(decoded);
    return printable ? decoded : null;
  } catch {
    return null;
  }
}

export function decodeMoveStringField(value: unknown) {
  if (typeof value !== "string" || value.length === 0) {
    return null;
  }

  if (value.startsWith("0x")) {
    return value;
  }

  return tryDecodeAsciiBase64(value) ?? value;
}

function decodeObjectIdField(value: unknown) {
  if (typeof value === "string" && value.length > 0) {
    return value;
  }

  if (isRecord(value)) {
    const nestedId = value.id;
    if (typeof nestedId === "string" && nestedId.length > 0) {
      return nestedId;
    }
  }

  return null;
}

export function decodeOwnedProofObject(
  object: OwnedProofObject,
  fallbackOwner: string,
): OwnedProofMetadata | null {
  const payload = object.json;
  if (!isRecord(payload)) {
    return null;
  }

  const owner = decodeMoveStringField(payload.owner) ?? fallbackOwner;
  const walrusBlobId = decodeMoveStringField(payload.walrus_blob_id);
  const walrusBlobObjectId = decodeObjectIdField(payload.walrus_blob_object_id);
  const sealIdentity = decodeMoveStringField(payload.seal_identity);
  const evidenceSchemaVersion = toNumber(payload.evidence_schema_version);
  const modelHash = decodeMoveStringField(payload.model_hash);
  const confidenceBps = toNumber(payload.confidence_bps);
  const issuedAtMs = toNumber(payload.issued_at_ms);
  const expiresAtMs = toNumber(payload.expires_at_ms);
  const challengeType = decodeMoveStringField(payload.challenge_type);

  if (
    !walrusBlobId ||
    !walrusBlobObjectId ||
    !sealIdentity ||
    evidenceSchemaVersion == null ||
    !modelHash ||
    confidenceBps == null ||
    issuedAtMs == null ||
    expiresAtMs == null ||
    !challengeType
  ) {
    return null;
  }

  return {
    proofId: object.objectId,
    owner,
    walrusBlobId,
    walrusBlobObjectId,
    sealIdentity,
    evidenceSchemaVersion,
    modelHash,
    confidenceBps,
    issuedAtMs,
    expiresAtMs,
    challengeType,
    transactionDigest: object.previousTransaction ?? null,
  };
}

export function isActiveOwnedProof(proof: OwnedProofMetadata, nowMs = Date.now()) {
  return proof.expiresAtMs > nowMs;
}

export function selectLatestActiveProof(
  proofs: OwnedProofMetadata[],
  nowMs = Date.now(),
): OwnedProofMetadata | null {
  const active = proofs.filter((proof) => isActiveOwnedProof(proof, nowMs));
  if (active.length === 0) {
    return null;
  }

  return active.slice().sort((left, right) => right.expiresAtMs - left.expiresAtMs)[0] ?? null;
}

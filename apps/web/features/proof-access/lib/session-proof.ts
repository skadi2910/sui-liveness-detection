import type { SessionRecordResponse } from "@sui-human/shared";

import type { OwnedProofMetadata } from "./types";

export function deriveOwnedProofFromSession(
  session: SessionRecordResponse | null,
  ownerAddress: string,
): OwnedProofMetadata | null {
  if (!session?.result) {
    return null;
  }

  const result = session.result;
  if (result.status !== "verified" || !result.proof_id) {
    return null;
  }

  if (
    !result.walrus_blob_id ||
    !result.walrus_blob_object_id ||
    !result.seal_identity ||
    !result.model_hash ||
    !result.expires_at
  ) {
    return null;
  }

  const expiresAtMs = Date.parse(result.expires_at);
  if (!Number.isFinite(expiresAtMs)) {
    return null;
  }

  const issuedAtMs = Date.parse(session.created_at);
  if (!Number.isFinite(issuedAtMs)) {
    return null;
  }

  return {
    proofId: result.proof_id,
    owner: ownerAddress,
    walrusBlobId: result.walrus_blob_id,
    walrusBlobObjectId: result.walrus_blob_object_id,
    sealIdentity: result.seal_identity,
    evidenceSchemaVersion: result.evidence_schema_version ?? 1,
    modelHash: result.model_hash,
    confidenceBps: Math.round(result.confidence * 10_000),
    issuedAtMs,
    expiresAtMs,
    challengeType: result.challenge_type,
    transactionDigest: result.transaction_digest ?? null,
  };
}

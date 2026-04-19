import type { VerificationResult } from "@sui-human/shared";

export type VerificationResultWithProofMetadata = VerificationResult & {
  proof_operation?: "minted" | "renewed";
  chain_network?: string | null;
};

export function getProofMetadataResult(
  result: VerificationResult | null | undefined,
): VerificationResultWithProofMetadata | null {
  return result ? (result as VerificationResultWithProofMetadata) : null;
}

export function formatProofOperation(value: string | null | undefined) {
  if (value === "renewed") return "Renewed";
  if (value === "minted") return "Minted";
  return "Unavailable";
}

export function formatProofValue(value: string | null | undefined, empty = "Unavailable") {
  return value && value.trim().length > 0 ? value : empty;
}

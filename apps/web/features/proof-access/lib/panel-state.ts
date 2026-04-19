import type { ProofDecryptState, ProofLoadState } from "./types";

export type OwnerDecryptPanelStatus =
  | "wallet_disconnected"
  | "config_missing"
  | "loading_proof"
  | "no_active_proof"
  | "proof_ready"
  | "awaiting_wallet_approval"
  | "decrypting"
  | "decrypted"
  | "decrypt_failed"
  | "proof_error";

export function deriveOwnerDecryptPanelStatus(params: {
  isWalletConnected: boolean;
  proofLoadState: ProofLoadState;
  decryptState: ProofDecryptState;
}) {
  if (!params.isWalletConnected) {
    return "wallet_disconnected" satisfies OwnerDecryptPanelStatus;
  }
  if (params.proofLoadState === "config_missing") {
    return "config_missing" satisfies OwnerDecryptPanelStatus;
  }
  if (params.proofLoadState === "loading") {
    return "loading_proof" satisfies OwnerDecryptPanelStatus;
  }
  if (params.proofLoadState === "error") {
    return "proof_error" satisfies OwnerDecryptPanelStatus;
  }
  if (params.decryptState === "awaiting_wallet_approval") {
    return "awaiting_wallet_approval" satisfies OwnerDecryptPanelStatus;
  }
  if (params.decryptState === "decrypting") {
    return "decrypting" satisfies OwnerDecryptPanelStatus;
  }
  if (params.decryptState === "success") {
    return "decrypted" satisfies OwnerDecryptPanelStatus;
  }
  if (params.decryptState === "error") {
    return "decrypt_failed" satisfies OwnerDecryptPanelStatus;
  }
  if (params.proofLoadState === "empty") {
    return "no_active_proof" satisfies OwnerDecryptPanelStatus;
  }
  return "proof_ready" satisfies OwnerDecryptPanelStatus;
}

import { fromBase64 } from "@mysten/bcs";
import type { PreparedProofClaim } from "@sui-human/shared";
import { Transaction } from "@mysten/sui/transactions";

type WalletTxResult =
  | {
      $kind: "Transaction";
      Transaction: {
        digest: string;
      };
    }
  | {
      $kind: "FailedTransaction";
      FailedTransaction: {
        status?: {
          error?: {
            message?: string | null;
          } | null;
        } | null;
      };
    };

function utf8Bytes(value: string) {
  return new TextEncoder().encode(value);
}

export function buildMintClaimTransaction(claim: PreparedProofClaim) {
  const tx = new Transaction();
  const target =
    claim.operation === "renew"
      ? `${claim.package_id}::${claim.module_name}::claim_and_renew`
      : `${claim.package_id}::${claim.module_name}::claim_and_mint`;

  const commonArgs = [
    tx.object(claim.registry_object_id),
    tx.object(claim.clock_object_id),
  ];

  const tailArgs = [
    tx.pure.vector("u8", utf8Bytes(claim.claim_id)),
    tx.pure.u64(claim.claim_expires_at_ms),
    tx.pure.address(claim.wallet_address),
    tx.pure.vector("u8", utf8Bytes(claim.walrus_blob_id)),
    tx.pure.id(claim.walrus_blob_object_id),
    tx.pure.vector("u8", utf8Bytes(claim.seal_identity)),
    tx.pure.u16(claim.evidence_schema_version),
    tx.pure.vector("u8", utf8Bytes(claim.model_hash ?? "")),
    tx.pure.u64(claim.confidence_bps),
    tx.pure.u64(claim.issued_at_ms),
    tx.pure.u64(claim.expires_at_ms),
    tx.pure.vector("u8", utf8Bytes(claim.challenge_type)),
    tx.pure.vector("u8", fromBase64(claim.signature_b64)),
  ];

  tx.moveCall({
    target,
    arguments:
      claim.operation === "renew" && claim.proof_object_id
        ? [
            ...commonArgs,
            tx.object(claim.proof_object_id),
            tailArgs[0],
            tailArgs[1],
            tailArgs[2],
            tx.pure.id(claim.proof_object_id),
            ...tailArgs.slice(3),
          ]
        : [...commonArgs, ...tailArgs],
  });

  return tx;
}

export async function signAndExecuteMintClaim(params: {
  claim: PreparedProofClaim;
  dAppKit: {
    signAndExecuteTransaction: (args: { transaction: Transaction }) => Promise<WalletTxResult>;
  };
}) {
  const result = await params.dAppKit.signAndExecuteTransaction({
    transaction: buildMintClaimTransaction(params.claim),
  });

  if (result.$kind === "FailedTransaction") {
    throw new Error(
      result.FailedTransaction.status?.error?.message ?? "Wallet transaction failed.",
    );
  }

  return {
    digest: result.Transaction.digest,
    proofId: params.claim.operation === "renew" ? params.claim.proof_object_id : undefined,
  };
}

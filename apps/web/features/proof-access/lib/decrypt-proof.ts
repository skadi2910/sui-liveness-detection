import { fromHex } from "@mysten/bcs";
import { SealClient, SessionKey } from "@mysten/seal";
import type { SuiGrpcClient } from "@mysten/sui/grpc";
import { Transaction } from "@mysten/sui/transactions";
import type { OwnedProofMetadata, OwnerProofConfig, RetainedEvidenceBlob } from "./types";

export async function buildOwnerApprovalTransactionBytes(params: {
  client: SuiGrpcClient;
  packageId: string;
  proof: OwnedProofMetadata;
}) {
  const tx = new Transaction();

  tx.moveCall({
    target: `${params.packageId}::proof_of_human::seal_approve_owner`,
    arguments: [
      tx.object(params.proof.proofId),
      tx.pure.vector("u8", fromHex(params.proof.sealIdentity)),
    ],
  });

  return tx.build({
    client: params.client,
    onlyTransactionKind: true,
  });
}

export async function fetchWalrusEncryptedBlob(params: {
  aggregatorUrl: string;
  walrusBlobId: string;
  fetchFn?: typeof fetch;
}) {
  const fetchFn = params.fetchFn ?? fetch;
  const normalizedBase = params.aggregatorUrl.replace(/\/+$/, "");
  const response = await fetchFn(
    `${normalizedBase}/v1/blobs/${encodeURIComponent(params.walrusBlobId)}`,
  );

  if (!response.ok) {
    throw new Error(`Walrus fetch failed with ${response.status}`);
  }

  return new Uint8Array(await response.arrayBuffer());
}

export function parseRetainedEvidenceBytes(bytes: Uint8Array) {
  return JSON.parse(new TextDecoder().decode(bytes)) as RetainedEvidenceBlob;
}

export async function decryptOwnedProofEvidence(params: {
  client: SuiGrpcClient;
  dAppKit: {
    signPersonalMessage: (args: { message: Uint8Array }) => Promise<{ signature: string }>;
  };
  config: OwnerProofConfig;
  ownerAddress: string;
  proof: OwnedProofMetadata;
  fetchFn?: typeof fetch;
  createSealClient?: (args: {
    client: SuiGrpcClient;
    config: OwnerProofConfig;
  }) => Pick<SealClient, "decrypt">;
  createSessionKey?: typeof SessionKey.create;
  buildApprovalTx?: typeof buildOwnerApprovalTransactionBytes;
}) {
  if (!params.config.packageId) {
    throw new Error("Missing NEXT_PUBLIC_SUI_PACKAGE_ID");
  }
  if (!params.config.walrusAggregatorUrl) {
    throw new Error("Missing NEXT_PUBLIC_WALRUS_AGGREGATOR_URL");
  }

  const createSealClient =
    params.createSealClient ??
    ((input: { client: SuiGrpcClient; config: OwnerProofConfig }) =>
      new SealClient({
        suiClient: input.client,
        serverConfigs: input.config.sealServerConfigs,
        verifyKeyServers: input.config.verifyKeyServers,
      }));

  const createSessionKey = params.createSessionKey ?? SessionKey.create;
  const buildApprovalTx = params.buildApprovalTx ?? buildOwnerApprovalTransactionBytes;

  const sessionKey = await createSessionKey({
    address: params.ownerAddress,
    packageId: params.config.packageId,
    ttlMin: params.config.sessionKeyTtlMinutes,
    suiClient: params.client,
  });

  const { signature } = await params.dAppKit.signPersonalMessage({
    message: sessionKey.getPersonalMessage(),
  });
  await sessionKey.setPersonalMessageSignature(signature);

  const txBytes = await buildApprovalTx({
    client: params.client,
    packageId: params.config.packageId,
    proof: params.proof,
  });
  const encryptedBytes = await fetchWalrusEncryptedBlob({
    aggregatorUrl: params.config.walrusAggregatorUrl,
    walrusBlobId: params.proof.walrusBlobId,
    fetchFn: params.fetchFn,
  });

  const decryptedBytes = await createSealClient({
    client: params.client,
    config: params.config,
  }).decrypt({
    data: encryptedBytes,
    sessionKey,
    txBytes,
  });

  return parseRetainedEvidenceBytes(decryptedBytes);
}

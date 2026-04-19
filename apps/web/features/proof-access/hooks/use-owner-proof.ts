"use client";

import { startTransition, useEffect, useMemo, useState } from "react";
import { useCurrentClient, useDAppKit } from "@mysten/dapp-kit-react";
import type { SuiGrpcClient } from "@mysten/sui/grpc";
import { useSuiWallet } from "@/features/wallet/hooks/use-sui-wallet";
import { fetchBrowserSession, readStoredSessionId } from "@/features/verifier-core/lib/app-session";
import { resolveOwnerProofConfig } from "../lib/config";
import { decryptOwnedProofEvidence } from "../lib/decrypt-proof";
import { decodeOwnedProofObject, selectLatestActiveProof } from "../lib/owned-proof";
import { deriveOwnedProofFromSession } from "../lib/session-proof";
import type {
  OwnedProofMetadata,
  ProofDecryptState,
  ProofLoadState,
  RetainedEvidenceBlob,
} from "../lib/types";

async function loadLatestOwnedProof(params: {
  client: SuiGrpcClient;
  ownerAddress: string;
  proofType: string;
}) {
  let cursor: string | null = null;
  const proofs: OwnedProofMetadata[] = [];
  let pageCount = 0;

  while (pageCount < 10) {
    const response: Awaited<ReturnType<SuiGrpcClient["listOwnedObjects"]>> =
      await params.client.listOwnedObjects({
      owner: params.ownerAddress,
      type: params.proofType,
      cursor,
      limit: 50,
      include: {
        json: true,
        previousTransaction: true,
      },
    });

    proofs.push(
      ...response.objects.flatMap((object) => {
        const decoded = decodeOwnedProofObject(object, params.ownerAddress);
        return decoded ? [decoded] : [];
      }),
    );

    pageCount += 1;
    if (!response.hasNextPage || !response.cursor) {
      break;
    }
    cursor = response.cursor;
  }

  return selectLatestActiveProof(proofs);
}

export function useOwnerProof() {
  const wallet = useSuiWallet();
  const client = useCurrentClient() as SuiGrpcClient;
  const dAppKit = useDAppKit();
  const config = useMemo(() => resolveOwnerProofConfig(), []);
  const [proofLoadState, setProofLoadState] = useState<ProofLoadState>(
    config.missing.length > 0 ? "config_missing" : "idle",
  );
  const [proofError, setProofError] = useState<string | null>(null);
  const [latestProof, setLatestProof] = useState<OwnedProofMetadata | null>(null);
  const [decryptState, setDecryptState] = useState<ProofDecryptState>("idle");
  const [decryptError, setDecryptError] = useState<string | null>(null);
  const [decryptedEvidence, setDecryptedEvidence] = useState<RetainedEvidenceBlob | null>(null);

  useEffect(() => {
    if (!wallet.isConnected || !wallet.address) {
      setLatestProof(null);
      setDecryptedEvidence(null);
      setProofError(null);
      setDecryptError(null);
      setProofLoadState(config.missing.length > 0 ? "config_missing" : "idle");
      setDecryptState("idle");
      return;
    }

    if (!config.proofType || config.missing.length > 0) {
      setLatestProof(null);
      setProofLoadState("config_missing");
      setProofError(
        `Missing public proof access config: ${config.missing.join(", ")}`,
      );
      return;
    }

    let cancelled = false;
    const proofType = config.proofType;
    if (!proofType) {
      setLatestProof(null);
      setProofLoadState("config_missing");
      setProofError("Missing NEXT_PUBLIC_SUI_PACKAGE_ID");
      return;
    }

    async function loadProof() {
      setProofLoadState("loading");
      setProofError(null);

      try {
        const proof = await loadLatestOwnedProof({
          client,
          ownerAddress: wallet.address!,
          proofType,
        });

        if (cancelled) {
          return;
        }

        let resolvedProof = proof;
        if (!resolvedProof) {
          const storedSessionId = readStoredSessionId();
          if (storedSessionId) {
            const storedSession = await fetchBrowserSession(storedSessionId);
            resolvedProof = deriveOwnedProofFromSession(storedSession, wallet.address!);
          }
        }

        setLatestProof(resolvedProof);
        setDecryptedEvidence(null);
        setDecryptError(null);
        setDecryptState("idle");
        setProofLoadState(resolvedProof ? "ready" : "empty");
      } catch (error) {
        if (cancelled) {
          return;
        }

        const storedSessionId = readStoredSessionId();
        if (storedSessionId) {
          try {
            const storedSession = await fetchBrowserSession(storedSessionId);
            const fallbackProof = deriveOwnedProofFromSession(storedSession, wallet.address!);
            if (fallbackProof) {
              setLatestProof(fallbackProof);
              setDecryptedEvidence(null);
              setDecryptError(null);
              setDecryptState("idle");
              setProofLoadState("ready");
              return;
            }
          } catch {
            // Ignore fallback errors and preserve the original lookup failure below.
          }
        }

        setLatestProof(null);
        setProofLoadState("error");
        setProofError(error instanceof Error ? error.message : "Failed to load owned proof");
      }
    }

    void loadProof();

    return () => {
      cancelled = true;
    };
  }, [client, config.missing, config.proofType, wallet.address, wallet.isConnected]);

  async function decryptLatestProof() {
    if (!wallet.address || !latestProof) {
      return;
    }

    setDecryptError(null);
    setDecryptState("awaiting_wallet_approval");

    try {
      const evidence = await decryptOwnedProofEvidence({
        client,
        dAppKit,
        config,
        ownerAddress: wallet.address,
        proof: latestProof,
      });

      startTransition(() => {
        setDecryptedEvidence(evidence);
        setDecryptState("success");
      });
    } catch (error) {
      setDecryptState("error");
      setDecryptError(
        error instanceof Error ? error.message : "Failed to decrypt evidence",
      );
    }
  }

  return {
    config,
    decryptError,
    decryptLatestProof,
    decryptState,
    decryptedEvidence,
    latestProof,
    proofError,
    proofLoadState,
    wallet,
  };
}

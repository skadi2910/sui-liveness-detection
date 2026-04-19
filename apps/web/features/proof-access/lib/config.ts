import { resolveSuiNetwork, resolveSuiRpcUrl } from "@/features/wallet/lib/config";
import type { OwnerProofConfig, SealServerConfig } from "./types";

const DEFAULT_TESTNET_WALRUS_AGGREGATOR_URL = "https://aggregator.walrus-testnet.walrus.space";

const DEFAULT_TESTNET_SEAL_SERVER_CONFIGS: SealServerConfig[] = [
  {
    objectId: "0xb012378c9f3799fb5b1a7083da74a4069e3c3f1c93de0b27212a5799ce1e1e98",
    aggregatorUrl: "https://seal-aggregator-testnet.mystenlabs.com",
    weight: 1,
  },
];

function parseBoolean(value: string | undefined, fallback = false) {
  if (!value) return fallback;
  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
}

function parsePositiveInt(value: string | undefined, fallback: number) {
  if (!value) return fallback;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function parseSealServerConfigs(
  rawValue: string | undefined,
  network: string,
): SealServerConfig[] {
  if (!rawValue?.trim()) {
    return network === "testnet" ? DEFAULT_TESTNET_SEAL_SERVER_CONFIGS : [];
  }

  try {
    const parsed = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.flatMap((entry) => {
      if (!entry || typeof entry !== "object") {
        return [];
      }

      const candidate = entry as Record<string, unknown>;
      if (
        typeof candidate.objectId !== "string" ||
        !candidate.objectId ||
        !Number.isFinite(candidate.weight)
      ) {
        return [];
      }

      return [
        {
          objectId: candidate.objectId,
          weight: Number(candidate.weight),
          ...(typeof candidate.aggregatorUrl === "string" && candidate.aggregatorUrl
            ? { aggregatorUrl: candidate.aggregatorUrl }
            : {}),
          ...(typeof candidate.apiKeyName === "string" && candidate.apiKeyName
            ? { apiKeyName: candidate.apiKeyName }
            : {}),
          ...(typeof candidate.apiKey === "string" && candidate.apiKey
            ? { apiKey: candidate.apiKey }
            : {}),
        },
      ];
    });
  } catch {
    return [];
  }
}

export function resolveOwnerProofConfig(
  env: Record<string, string | undefined> = process.env,
): OwnerProofConfig {
  const network = resolveSuiNetwork(env.NEXT_PUBLIC_SUI_NETWORK);
  const fullnodeUrl = resolveSuiRpcUrl({
    envValue: env.NEXT_PUBLIC_SUI_FULLNODE_URL ?? env.NEXT_PUBLIC_SUI_RPC_URL,
    network,
  });
  const packageId = env.NEXT_PUBLIC_SUI_PACKAGE_ID?.trim() ?? null;
  const walrusAggregatorUrl =
    env.NEXT_PUBLIC_WALRUS_AGGREGATOR_URL?.trim() ??
    (network === "testnet" ? DEFAULT_TESTNET_WALRUS_AGGREGATOR_URL : null);
  const sealServerConfigs = parseSealServerConfigs(env.NEXT_PUBLIC_SEAL_SERVER_CONFIGS, network);
  const sealThreshold = parsePositiveInt(env.NEXT_PUBLIC_SEAL_THRESHOLD, 1);
  const sessionKeyTtlMinutes = parsePositiveInt(env.NEXT_PUBLIC_SEAL_SESSION_KEY_TTL_MINUTES, 10);
  const verifyKeyServers = parseBoolean(env.NEXT_PUBLIC_SEAL_VERIFY_KEY_SERVERS, false);

  const missing = [
    packageId ? null : "NEXT_PUBLIC_SUI_PACKAGE_ID",
    walrusAggregatorUrl ? null : "NEXT_PUBLIC_WALRUS_AGGREGATOR_URL",
    sealServerConfigs.length > 0 ? null : "NEXT_PUBLIC_SEAL_SERVER_CONFIGS",
  ].filter((value): value is string => Boolean(value));

  return {
    packageId,
    network,
    fullnodeUrl,
    walrusAggregatorUrl,
    sealServerConfigs,
    sealThreshold,
    verifyKeyServers,
    sessionKeyTtlMinutes,
    proofType: packageId ? `${packageId}::proof_of_human::ProofOfHuman` : null,
    missing,
  };
}


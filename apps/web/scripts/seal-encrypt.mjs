import { createHash } from "node:crypto";
import process from "node:process";

import { SealClient } from "@mysten/seal";
import { SuiGrpcClient } from "@mysten/sui/grpc";

function printHelp() {
  process.stdout.write(`Seal encrypt helper

Reads JSON from stdin and returns JSON for the verifier's Seal command adapter.

Input:
  {
    "wallet_address": "0x...",
    "payload_b64": "<base64 payload bytes>",
    "policy_version": "seal-v1"
  }

Output:
  {
    "encrypted_bytes_b64": "<base64 encrypted object bytes>",
    "seal_identity": "0x...",
    "policy_version": "seal-v1",
    "metadata": { ... }
  }

Required environment:
  VERIFIER_SUI_PACKAGE_ID or SEAL_HELPER_PACKAGE_ID
  VERIFIER_SEAL_SERVER_CONFIGS or SEAL_HELPER_SERVER_CONFIGS

Optional environment:
  VERIFIER_SEAL_SUI_BASE_URL
  VERIFIER_SEAL_SUI_NETWORK
  VERIFIER_SEAL_THRESHOLD
  VERIFIER_SEAL_VERIFY_KEY_SERVERS
  VERIFIER_SEAL_TIMEOUT_MS
  VERIFIER_SEAL_ID_SALT
`);
}

function parseBool(value, fallback = false) {
  if (value == null || value === "") {
    return fallback;
  }
  const normalized = String(value).trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(normalized);
}

function parsePositiveInt(value, fallback) {
  if (value == null || value === "") {
    return fallback;
  }
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`expected a positive integer, received ${value}`);
  }
  return parsed;
}

function parseServerConfigs() {
  const raw =
    process.env.VERIFIER_SEAL_SERVER_CONFIGS ?? process.env.SEAL_HELPER_SERVER_CONFIGS;
  if (!raw) {
    throw new Error(
      "missing VERIFIER_SEAL_SERVER_CONFIGS or SEAL_HELPER_SERVER_CONFIGS",
    );
  }
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("seal server config JSON must be a non-empty array");
  }
  return parsed.map((config, index) => {
    if (!config || typeof config !== "object") {
      throw new Error(`seal server config at index ${index} must be an object`);
    }
    if (typeof config.objectId !== "string" || config.objectId.length === 0) {
      throw new Error(`seal server config at index ${index} is missing objectId`);
    }
    if (!Number.isFinite(config.weight) || config.weight <= 0) {
      throw new Error(`seal server config at index ${index} has invalid weight`);
    }
    return {
      objectId: config.objectId,
      weight: config.weight,
      ...(typeof config.aggregatorUrl === "string" && config.aggregatorUrl
        ? { aggregatorUrl: config.aggregatorUrl }
        : {}),
      ...(typeof config.apiKeyName === "string" && config.apiKeyName
        ? { apiKeyName: config.apiKeyName }
        : {}),
      ...(typeof config.apiKey === "string" && config.apiKey
        ? { apiKey: config.apiKey }
        : {}),
    };
  });
}

async function readStdin() {
  let data = "";
  for await (const chunk of process.stdin) {
    data += chunk;
  }
  return data;
}

function deriveSealIdentity({ packageId, walletAddress, payloadBytes, salt }) {
  const digest = createHash("sha256")
    .update(packageId)
    .update("\0")
    .update(walletAddress)
    .update("\0")
    .update(payloadBytes)
    .update("\0")
    .update(salt)
    .digest("hex");
  return `0x${digest}`;
}

function normalizeNetwork(value) {
  const normalized = String(value ?? "testnet").trim().toLowerCase();
  if (normalized === "sui-testnet") {
    return "testnet";
  }
  if (normalized === "sui-mainnet") {
    return "mainnet";
  }
  if (normalized === "sui-devnet") {
    return "devnet";
  }
  if (normalized === "sui-localnet") {
    return "localnet";
  }
  return normalized;
}

async function main() {
  if (process.argv.includes("--help")) {
    printHelp();
    return;
  }

  const packageId =
    process.env.VERIFIER_SUI_PACKAGE_ID ?? process.env.SEAL_HELPER_PACKAGE_ID;
  if (!packageId) {
    throw new Error("missing VERIFIER_SUI_PACKAGE_ID or SEAL_HELPER_PACKAGE_ID");
  }

  const baseUrl =
    process.env.VERIFIER_SEAL_SUI_BASE_URL ??
    process.env.SEAL_HELPER_SUI_BASE_URL ??
    process.env.VERIFIER_SEAL_SUI_RPC_URL ??
    process.env.SEAL_HELPER_SUI_RPC_URL ??
    "https://fullnode.testnet.sui.io:443";
  const network = normalizeNetwork(
    process.env.VERIFIER_SEAL_SUI_NETWORK ??
      process.env.SEAL_HELPER_SUI_NETWORK ??
      process.env.VERIFIER_SUI_NETWORK ??
      "testnet",
  );
  const serverConfigs = parseServerConfigs();
  const totalWeight = serverConfigs.reduce((sum, config) => sum + config.weight, 0);
  const threshold = parsePositiveInt(
    process.env.VERIFIER_SEAL_THRESHOLD ?? process.env.SEAL_HELPER_THRESHOLD,
    Math.min(2, totalWeight || 1),
  );
  const verifyKeyServers = parseBool(
    process.env.VERIFIER_SEAL_VERIFY_KEY_SERVERS ??
      process.env.SEAL_HELPER_VERIFY_KEY_SERVERS,
    false,
  );
  const timeout = parsePositiveInt(
    process.env.VERIFIER_SEAL_TIMEOUT_MS ?? process.env.SEAL_HELPER_TIMEOUT_MS,
    10_000,
  );
  const identitySalt =
    process.env.VERIFIER_SEAL_ID_SALT ?? process.env.SEAL_HELPER_ID_SALT ?? "";

  const rawInput = await readStdin();
  if (!rawInput.trim()) {
    throw new Error("expected JSON input on stdin");
  }

  const input = JSON.parse(rawInput);
  if (typeof input.wallet_address !== "string" || input.wallet_address.length === 0) {
    throw new Error("input.wallet_address is required");
  }
  if (typeof input.payload_b64 !== "string" || input.payload_b64.length === 0) {
    throw new Error("input.payload_b64 is required");
  }

  const payloadBytes = Buffer.from(input.payload_b64, "base64");
  const sealIdentity = deriveSealIdentity({
    packageId,
    walletAddress: input.wallet_address,
    payloadBytes,
    salt: identitySalt,
  });

  const client = new SealClient({
    suiClient: new SuiGrpcClient({ network, baseUrl }),
    serverConfigs,
    verifyKeyServers,
    timeout,
  });

  const { encryptedObject } = await client.encrypt({
    threshold,
    packageId,
    id: sealIdentity,
    data: new Uint8Array(payloadBytes),
  });

  process.stdout.write(
    `${JSON.stringify(
      {
        encrypted_bytes_b64: Buffer.from(encryptedObject).toString("base64"),
        seal_identity: sealIdentity,
        policy_version: input.policy_version ?? process.env.VERIFIER_SEAL_POLICY_VERSION ?? "seal-v1",
        metadata: {
          wallet_address: input.wallet_address,
          package_id: packageId,
          network,
          base_url: baseUrl,
          threshold,
          key_server_object_ids: serverConfigs.map((config) => config.objectId),
          verify_key_servers: verifyKeyServers,
        },
      },
      null,
      2,
    )}\n`,
  );
}

main().catch((error) => {
  const message = error instanceof Error ? error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});

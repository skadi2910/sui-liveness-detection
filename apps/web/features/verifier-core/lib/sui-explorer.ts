function normalizeExplorerNetwork(value: string | null | undefined) {
  const normalized = (value ?? "testnet").trim().toLowerCase();
  if (normalized === "mainnet" || normalized === "testnet" || normalized === "devnet") {
    return normalized;
  }
  if (normalized.startsWith("sui-")) {
    return normalizeExplorerNetwork(normalized.slice(4));
  }
  return "testnet";
}

function buildExplorerUrl(kind: "object" | "tx", id: string, network: string | null | undefined) {
  const trimmed = id.trim();
  if (!trimmed) return null;
  return `https://suiscan.xyz/${normalizeExplorerNetwork(network)}/${kind}/${trimmed}`;
}

export function buildSuiscanObjectUrl(
  proofId: string | null | undefined,
  network: string | null | undefined,
) {
  if (!proofId) return null;
  return buildExplorerUrl("object", proofId, network);
}

export function buildSuiscanTransactionUrl(
  transactionDigest: string | null | undefined,
  network: string | null | undefined,
) {
  if (!transactionDigest) return null;
  return buildExplorerUrl("tx", transactionDigest, network);
}

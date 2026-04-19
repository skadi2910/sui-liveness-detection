export const supportedSuiNetworks = [
  "mainnet",
  "testnet",
  "devnet",
  "localnet",
] as const;

export type SupportedSuiNetwork = (typeof supportedSuiNetworks)[number];

const networkRpcUrls: Record<SupportedSuiNetwork, string> = {
  mainnet: "https://fullnode.mainnet.sui.io:443",
  testnet: "https://fullnode.testnet.sui.io:443",
  devnet: "https://fullnode.devnet.sui.io:443",
  localnet: "http://127.0.0.1:9000",
};

export function isSupportedSuiNetwork(value: string): value is SupportedSuiNetwork {
  return supportedSuiNetworks.includes(value as SupportedSuiNetwork);
}

export function resolveSuiNetwork(value: string | undefined): SupportedSuiNetwork {
  if (value && isSupportedSuiNetwork(value)) {
    return value;
  }

  return "testnet";
}

export function resolveSuiRpcUrl(params?: {
  envValue?: string;
  network?: SupportedSuiNetwork;
}) {
  if (params?.envValue) {
    return params.envValue;
  }

  return networkRpcUrls[params?.network ?? "testnet"];
}

export function formatSuiNetworkLabel(network: string | null | undefined) {
  if (!network) return "No network";
  return network.replace(/net$/i, "net").replace(/^./, (value) => value.toUpperCase());
}

export function shortenWalletAddress(address: string | null | undefined) {
  if (!address) return "Wallet disconnected";
  if (address.length <= 14) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

export function hasConnectedWallet(address: string | null | undefined) {
  return Boolean(address && address.trim().length > 0);
}

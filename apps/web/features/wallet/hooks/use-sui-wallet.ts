"use client";

import { useMemo } from "react";
import {
  useCurrentAccount,
  useCurrentNetwork,
  useDAppKit,
  useWalletConnection,
} from "@mysten/dapp-kit-react";
import {
  formatSuiNetworkLabel,
  hasConnectedWallet,
  shortenWalletAddress,
} from "../lib/config";

export function useSuiWallet() {
  const account = useCurrentAccount();
  const currentNetwork = useCurrentNetwork();
  const connection = useWalletConnection();
  const dAppKit = useDAppKit();

  const address = account?.address ?? null;
  const network = currentNetwork ?? null;
  const isConnected = hasConnectedWallet(address) && connection.status === "connected";
  const isConnecting =
    connection.status === "connecting" || connection.status === "reconnecting";

  return useMemo(
    () => ({
      account,
      address,
      connectionStatus: connection.status,
      disconnect: () => dAppKit.disconnectWallet(),
      isConnected,
      isConnecting,
      network,
      networkLabel: formatSuiNetworkLabel(network),
      shortAddress: shortenWalletAddress(address),
    }),
    [account, address, connection.status, dAppKit, isConnected, isConnecting, network],
  );
}

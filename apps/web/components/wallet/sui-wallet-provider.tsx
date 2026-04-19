"use client";

import type { ReactNode } from "react";
import { useMemo } from "react";
import { createDAppKit, DAppKitProvider } from "@mysten/dapp-kit-react";
import { SuiGrpcClient } from "@mysten/sui/grpc";
import {
  resolveSuiNetwork,
  resolveSuiRpcUrl,
  type SupportedSuiNetwork,
} from "@/features/wallet/lib/config";

function createSuiDAppKit() {
  const network = resolveSuiNetwork(process.env.NEXT_PUBLIC_SUI_NETWORK);

  return createDAppKit({
    autoConnect: true,
    defaultNetwork: network,
    networks: [network] satisfies SupportedSuiNetwork[],
    storageKey: "sui-human-dapp-kit",
    createClient: (selectedNetwork) =>
      new SuiGrpcClient({
        network: selectedNetwork,
        baseUrl: resolveSuiRpcUrl({
          envValue: process.env.NEXT_PUBLIC_SUI_RPC_URL,
          network: resolveSuiNetwork(selectedNetwork),
        }),
      }),
  });
}

type AppDAppKit = ReturnType<typeof createSuiDAppKit>;

declare module "@mysten/dapp-kit-react" {
  interface Register {
    dAppKit: AppDAppKit;
  }
}

export function SuiWalletProvider({ children }: { children: ReactNode }) {
  const dAppKit = useMemo(() => createSuiDAppKit(), []);

  return <DAppKitProvider dAppKit={dAppKit}>{children}</DAppKitProvider>;
}

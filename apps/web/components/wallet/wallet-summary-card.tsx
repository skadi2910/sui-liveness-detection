"use client";

import { useSuiWallet } from "@/features/wallet/hooks/use-sui-wallet";
import { WalletButtonSlot } from "./wallet-button-slot";

export function WalletSummaryCard() {
  const wallet = useSuiWallet();

  return (
    <div className="border border-line/60 bg-background/60 p-4">
      <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
        Wallet status
      </p>
      <p className="mt-3 font-headline text-2xl font-black uppercase tracking-tight text-foreground">
        {wallet.isConnected ? "Connected" : wallet.isConnecting ? "Connecting" : "Required"}
      </p>
      <p className="mt-3 text-sm leading-7 text-muted-foreground">
        {wallet.isConnected
          ? `Verification sessions will be created for ${wallet.shortAddress} on ${wallet.networkLabel}.`
          : "Connect a Sui wallet before starting a fresh verification session. Existing saved sessions can still be reviewed or cleared from this dashboard."}
      </p>
      <div className="mt-4">
        <WalletButtonSlot />
      </div>
    </div>
  );
}

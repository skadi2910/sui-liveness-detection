"use client";

import dynamic from "next/dynamic";

const WalletButton = dynamic(
  () => import("@/components/wallet/wallet-button").then((module) => module.WalletButton),
  {
    ssr: false,
    loading: () => (
      <div className="inline-flex items-center justify-center border border-line px-4 py-2 text-[0.6rem] uppercase tracking-[0.22em] text-muted-foreground">
        Wallet
      </div>
    ),
  },
);

export function WalletButtonSlot() {
  return <WalletButton />;
}

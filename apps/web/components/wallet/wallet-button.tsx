"use client";

import { useRef } from "react";
import { useDAppKit } from "@mysten/dapp-kit-react";
import { ConnectModal } from "@mysten/dapp-kit-react/ui";
import type { DAppKitConnectModal } from "@mysten/dapp-kit-core/web";
import { useSuiWallet } from "@/features/wallet/hooks/use-sui-wallet";

function buttonClassName(connected: boolean) {
  if (connected) {
    return "inline-flex items-center gap-3 border border-line bg-panel px-3 py-2 text-left transition hover:border-accent";
  }

  return "inline-flex items-center justify-center border border-accent bg-accent px-4 py-2 text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-accent-foreground transition hover:brightness-110";
}

export function WalletButton() {
  const dAppKit = useDAppKit();
  const modalRef = useRef<DAppKitConnectModal | null>(null);
  const wallet = useSuiWallet();

  function openModal() {
    void modalRef.current?.show();
  }

  async function disconnectWallet() {
    await wallet.disconnect();
  }

  return (
    <div className="wallet-skin flex items-center gap-2">
      <ConnectModal instance={dAppKit} ref={modalRef} />

      {wallet.isConnected ? (
        <>
          <button
            aria-label="Manage connected Sui wallet"
            className={buttonClassName(true)}
            onClick={openModal}
            type="button"
          >
            <span className="grid">
              <span className="text-[0.55rem] uppercase tracking-[0.22em] text-muted-foreground">
                {wallet.networkLabel}
              </span>
              <span className="font-headline text-sm font-black uppercase tracking-tight text-foreground">
                {wallet.shortAddress}
              </span>
            </span>
          </button>
          <button
            className="inline-flex items-center justify-center border border-line px-3 py-2 text-[0.6rem] uppercase tracking-[0.22em] text-muted-foreground transition hover:border-accent hover:text-foreground"
            onClick={() => void disconnectWallet()}
            type="button"
          >
            Disconnect
          </button>
        </>
      ) : (
        <button
          className={buttonClassName(false)}
          onClick={openModal}
          type="button"
        >
          {wallet.isConnecting ? "Connecting..." : "Connect wallet"}
        </button>
      )}
    </div>
  );
}

"use client";

import { startTransition, useState } from "react";
import { useRouter } from "next/navigation";
import { createBrowserSession } from "@/features/verifier-core/lib/app-session";
import { useSuiWallet } from "@/features/wallet/hooks/use-sui-wallet";

type Variant = "primary" | "secondary";

function buttonClassName(variant: Variant) {
  if (variant === "secondary") {
    return "inline-flex items-center justify-center border border-line bg-panel px-5 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-foreground transition hover:border-accent hover:text-accent";
  }

  return "inline-flex items-center justify-center border border-accent bg-accent px-5 py-3 text-[0.7rem] uppercase tracking-[0.28em] text-accent-foreground transition hover:brightness-110";
}

export function LaunchVerificationButton(props: {
  className?: string;
  label?: string;
  variant?: Variant;
}) {
  const router = useRouter();
  const wallet = useSuiWallet();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    if (!wallet.address) {
      startTransition(() => {
        router.push("/app");
      });
      return;
    }

    setPending(true);
    setError(null);

    try {
      const payload = await createBrowserSession({ walletAddress: wallet.address });
      startTransition(() => {
        router.push(`/verify/${payload.session_id}`);
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start verification.");
      setPending(false);
    }
  }

  return (
    <div className={props.className}>
      <button
        className={buttonClassName(props.variant ?? "primary")}
        disabled={pending}
        onClick={() => void handleStart()}
        type="button"
      >
        {pending
          ? "Starting..."
          : props.label ?? (wallet.address ? "Launch verification" : "Open app")}
      </button>
      {error ? (
        <p className="mt-2 text-xs text-danger">{error}</p>
      ) : null}
    </div>
  );
}

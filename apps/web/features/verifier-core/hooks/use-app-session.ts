"use client";

import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import type { SessionRecordResponse } from "@sui-human/shared";
import { useRouter } from "next/navigation";
import {
  clearStoredSessionId,
  createBrowserSession,
  describeAppSession,
  deriveAppRouteTarget,
  fetchBrowserSession,
  readStoredSessionId,
} from "../lib/app-session";

type LoadState = "loading" | "ready" | "starting" | "error";

export function useAppSession() {
  const router = useRouter();
  const hydratedRef = useRef(false);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<SessionRecordResponse | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  async function restoreStoredSession() {
    setError(null);
    setLoadState("loading");
    const stored = readStoredSessionId();
    setSessionId(stored);

    if (!stored) {
      setSession(null);
      setLoadState("ready");
      return;
    }

    try {
      const existing = await fetchBrowserSession(stored);
      setSession(existing);
      setLoadState("ready");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not restore session.");
      setLoadState("error");
    }
  }

  async function startSession() {
    return startSessionWithWallet();
  }

  async function startSessionWithWallet(walletAddress?: string | null) {
    if (!walletAddress) {
      setError("Connect a Sui wallet before starting verification.");
      setLoadState("ready");
      return;
    }

    setLoadState("starting");
    setError(null);

    try {
      const created = await createBrowserSession({ walletAddress });
      setSessionId(created.session_id);
      startTransition(() => {
        router.push(`/verify/${created.session_id}`);
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start session.");
      setLoadState("error");
    }
  }

  function clearSession() {
    clearStoredSessionId();
    setSessionId(null);
    setSession(null);
    setError(null);
    setLoadState("ready");
  }

  useEffect(() => {
    if (hydratedRef.current) return;
    hydratedRef.current = true;
    void restoreStoredSession();
  }, []);

  const routeTarget = useMemo(() => deriveAppRouteTarget(session), [session]);
  const sessionCopy = useMemo(() => describeAppSession(session), [session]);

  useEffect(() => {
    if (loadState !== "ready") return;
    if (routeTarget.kind !== "verify") return;

    startTransition(() => {
      router.replace(routeTarget.href);
    });
  }, [loadState, routeTarget, router]);

  return {
    clearSession,
    error,
    loadState,
    restoreStoredSession,
    routeTarget,
    session,
    sessionCopy,
    sessionId,
    startSession: startSessionWithWallet,
  };
}

"use client";

import type {
  ChallengeType,
  CreateSessionResponse,
  SessionRecordResponse,
} from "@sui-human/shared";
import { deriveResultOutcome } from "./client-flow";
import { demoWalletAddress, httpBase } from "./constants";

export const lastSessionStorageKey = "sui-human-last-session";

export type AppRouteTarget =
  | { kind: "missing" }
  | { kind: "verify"; href: string }
  | { kind: "result"; href: string }
  | { kind: "expired"; href: string };

export function readStoredSessionId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(lastSessionStorageKey);
}

export function storeSessionId(sessionId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(lastSessionStorageKey, sessionId);
}

export function clearStoredSessionId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(lastSessionStorageKey);
}

export async function createBrowserSession(params?: {
  challengeSequence?: ChallengeType[];
  walletAddress?: string;
}) {
  const response = await fetch(`${httpBase}/api/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      wallet_address: params?.walletAddress ?? demoWalletAddress,
      client: {
        platform: "web",
        user_agent: navigator.userAgent,
      },
      challenge_sequence:
        params?.challengeSequence && params.challengeSequence.length > 0
          ? params.challengeSequence
          : undefined,
    }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(payload.detail ?? "Could not create session");
  }

  const payload = (await response.json()) as CreateSessionResponse;
  storeSessionId(payload.session_id);
  return payload;
}

export async function fetchBrowserSession(sessionId: string) {
  const response = await fetch(`${httpBase}/api/sessions/${sessionId}`, {
    cache: "no-store",
  });

  if (response.status === 404) {
    clearStoredSessionId();
    return null;
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(payload.detail ?? "Could not load session");
  }

  return (await response.json()) as SessionRecordResponse;
}

export function deriveAppRouteTarget(session: SessionRecordResponse | null): AppRouteTarget {
  if (!session) return { kind: "missing" };

  if (session.status === "expired") {
    return { kind: "expired", href: `/result/${session.session_id}` };
  }

  if (session.result) {
    return { kind: "result", href: `/result/${session.session_id}` };
  }

  return { kind: "verify", href: `/verify/${session.session_id}` };
}

export function describeAppSession(session: SessionRecordResponse | null) {
  if (!session) {
    return {
      badge: "No session",
      title: "Ready for a fresh verification",
      detail:
        "Start a session from this dashboard to enter the live capture flow, then return here later for wallet handoff.",
    };
  }

  const route = deriveAppRouteTarget(session);
  const outcome = deriveResultOutcome(session);

  if (route.kind === "expired") {
    return {
      badge: "Expired",
      title: "Previous session expired",
      detail:
        "The last saved session can no longer continue. Start a fresh verification when you are ready.",
    };
  }

  if (route.kind === "result") {
    return {
      badge: outcome === "verified" ? "Verified" : outcome === "spoof" ? "Flagged" : "Finished",
      title:
        outcome === "verified"
          ? "Attestation is ready"
          : outcome === "spoof"
            ? "Review the verifier outcome"
            : "Session completed",
      detail:
        outcome === "verified"
          ? "A completed result is on file and ready for the next proof or wallet step."
          : "A terminal verifier result exists for this session. Review it before starting over.",
    };
  }

  return {
    badge: "In progress",
    title: "Resume your live verification",
    detail:
      "A non-terminal session is already saved for this device. Continue the capture flow where it left off.",
  };
}

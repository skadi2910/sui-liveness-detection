import { headers } from "next/headers";
import type { SessionRecordResponse } from "@sui-human/shared";
import { resolveVerifierHttpBase } from "./verifier-base";

export async function fetchSessionRecord(sessionId: string) {
  const headerList = await headers();
  const baseUrl = resolveVerifierHttpBase({
    envValue: process.env.NEXT_PUBLIC_VERIFIER_HTTP_URL,
    host: headerList.get("x-forwarded-host") ?? headerList.get("host"),
    protocol: headerList.get("x-forwarded-proto") ?? "http",
  });

  if (!baseUrl) {
    return null;
  }

  const response = await fetch(`${baseUrl}/api/sessions/${sessionId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as SessionRecordResponse;
}

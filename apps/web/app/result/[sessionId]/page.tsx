import { ResultSummary } from "@/components/result/result-summary";
import { SiteHeader } from "@/components/marketing/site-header";
import { fetchSessionRecord } from "@/lib/server-verifier";

export const dynamic = "force-dynamic";

export default async function ResultPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  const session = await fetchSessionRecord(sessionId);

  return (
    <>
      <SiteHeader compact />
      <ResultSummary session={session} sessionId={sessionId} />
    </>
  );
}

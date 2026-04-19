import ClientVerificationShell from "@/components/verification/client-verification-shell";

export default async function VerifyPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ClientVerificationShell sessionId={sessionId} />;
}

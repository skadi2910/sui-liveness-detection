export function resolveVerifierHttpBase(params: {
  envValue?: string;
  host?: string | null;
  protocol?: string | null;
}) {
  const envValue = params.envValue?.trim();
  const protocol = params.protocol ?? "http";
  const host = params.host ?? null;

  if (envValue) {
    if (envValue.startsWith("http://") || envValue.startsWith("https://")) {
      return envValue.replace(/\/$/, "");
    }

    if (envValue.startsWith("/")) {
      if (!host) return null;
      return `${protocol}://${host}${envValue}`.replace(/\/$/, "");
    }

    if (!host) return null;
    return `${protocol}://${host}/${envValue}`.replace(/\/$/, "");
  }

  if (!host) {
    return null;
  }

  if (host.startsWith("localhost:") || host === "localhost") {
    return "http://127.0.0.1:8000";
  }
  if (host.startsWith("127.0.0.1:") || host === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }

  return `${protocol}://${host}`;
}

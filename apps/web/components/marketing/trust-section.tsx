export function TrustSection() {
  return (
    <section className="border-b border-line/70" id="trust">
      <div className="mx-auto grid max-w-7xl gap-0 px-4 py-20 sm:px-6 lg:grid-cols-2">
        <article className="border border-line/70 bg-panel p-8 lg:border-r-0 lg:p-10">
          <p className="text-[0.68rem] uppercase tracking-[0.32em] text-accent">
            Privacy posture
          </p>
          <h2 className="mt-4 font-headline text-3xl font-black uppercase tracking-tight text-foreground sm:text-4xl">
            Clean client UX. Hardened verifier core.
          </h2>
          <p className="mt-5 max-w-xl text-sm leading-7 text-muted-foreground">
            The public flow does not expose server checks, calibration tools, or raw
            debug data. It stays focused on consent, motion guidance, and a clear
            attestation result.
          </p>
        </article>

        <article className="border border-line/70 bg-background/70 p-8 lg:p-10">
          <p className="text-[0.68rem] uppercase tracking-[0.32em] text-signal-cyan">
            Operational split
          </p>
          <h2 className="mt-4 font-headline text-3xl font-black uppercase tracking-tight text-foreground sm:text-4xl">
            Admin remains for QA and threshold tuning.
          </h2>
          <p className="mt-5 max-w-xl text-sm leading-7 text-muted-foreground">
            Engineering retains the richer console for sequence debugging, attack
            simulation, calibration export, and verifier health while the client route
            presents only the product-facing surface.
          </p>
        </article>
      </div>
    </section>
  );
}

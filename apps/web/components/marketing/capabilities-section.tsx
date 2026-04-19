export function CapabilitiesSection() {
  const items = [
    {
      label: "01",
      title: "AI liveness",
      body: "Real-time motion challenges verify that the subject can respond naturally on demand.",
    },
    {
      label: "02",
      title: "Behavioral checks",
      body: "Landmark-derived cues distinguish human response from scripted or replayed interactions.",
    },
    {
      label: "03",
      title: "Proof-ready result",
      body: "The client flow stays clean while the backend decides whether a session is trustworthy enough to proceed.",
    },
  ];

  return (
    <section className="border-b border-line/70" id="capabilities">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="mb-12 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-[0.68rem] uppercase tracking-[0.32em] text-accent">
              System capabilities
            </p>
            <h2 className="mt-3 font-headline text-4xl font-black uppercase tracking-tight text-foreground sm:text-5xl">
              The human pulse engine
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-7 text-muted-foreground">
            The public surface explains the product in plain language while the admin
            console remains dedicated to operator-grade telemetry and QA.
          </p>
        </div>

        <div className="grid gap-0 border border-line/70 lg:grid-cols-3">
          {items.map((item) => (
            <article
              className="group border-b border-line/70 bg-panel p-8 last:border-b-0 lg:border-b-0 lg:border-r last:lg:border-r-0"
              key={item.title}
            >
              <p className="text-[0.72rem] uppercase tracking-[0.32em] text-muted-foreground">
                {item.label}
              </p>
              <h3 className="mt-10 font-headline text-2xl font-bold uppercase tracking-tight text-foreground transition group-hover:text-accent">
                {item.title}
              </h3>
              <p className="mt-4 max-w-sm text-sm leading-7 text-muted-foreground">
                {item.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

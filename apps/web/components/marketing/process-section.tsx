export function ProcessSection() {
  const steps = [
    ["Open session", "Start from the client shell and grant camera access."],
    ["Follow motion", "Center your face and complete the live instruction sequence."],
    ["Receive result", "Finalize once complete and review the attestation verdict."],
  ];

  return (
    <section className="border-b border-line/70" id="process">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-20 sm:px-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <div className="lg:sticky lg:top-24 lg:self-start">
          <p className="text-[0.68rem] uppercase tracking-[0.32em] text-accent">
            Process
          </p>
          <h2 className="mt-4 font-headline text-4xl font-black uppercase tracking-tight text-foreground">
            Verification without dashboard clutter
          </h2>
          <p className="mt-5 text-sm leading-7 text-muted-foreground">
            The user sees only the camera, the active instruction, the session
            progress, and the final outcome. All diagnostic complexity stays in admin.
          </p>
        </div>

        <div className="grid gap-0 border border-line/70">
          {steps.map(([title, body], index) => (
            <div
              className="grid gap-4 border-b border-line/70 bg-panel p-6 last:border-b-0 sm:grid-cols-[4rem_minmax(0,1fr)] sm:p-8"
              key={title}
            >
              <div className="font-headline text-5xl font-black text-accent/70">
                {`0${index + 1}`}
              </div>
              <div>
                <h3 className="font-headline text-2xl font-bold uppercase tracking-tight text-foreground">
                  {title}
                </h3>
                <p className="mt-3 max-w-xl text-sm leading-7 text-muted-foreground">
                  {body}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

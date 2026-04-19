import { AppShell } from "@/components/chrome/app-shell";
import { ConsolePanel } from "@/components/chrome/console-panel";

const values = [
  {
    title: "Digital Sovereignty",
    body: "Identity should not be owned by a platform. The product experience must keep sensitive signal collection local and keep proof outputs portable.",
  },
  {
    title: "Radical Transparency",
    body: "The interface should explain what the verifier is doing and why, without turning the public flow into an internal ops console.",
  },
  {
    title: "Universal Access",
    body: "The verification journey should be legible on mobile, resilient in weak conditions, and welcoming instead of punitive.",
  },
] as const;

const team = [
  { name: "Vera Silvas", role: "Lead engineer" },
  { name: "Noah Kade", role: "Protocol architect" },
  { name: "Mika Rowan", role: "Identity systems" },
  { name: "Iris Vale", role: "Network operations" },
] as const;

export function AboutPage() {
  return (
    <AppShell
      activeSection="about"
      description="Sui Human exists to secure the human layer of on-chain participation. This page is intentionally editorial: it explains why the protocol exists, what values shape the UI, and who the product is being designed for before we overload it with system detail."
      eyebrow="Mission / Profile"
      meta={[
        { label: "Integrity index", value: "99.98%" },
        { label: "Oracle mesh", value: "142 active" },
        { label: "Clearance", value: "Omega" },
      ]}
      title="Secure the Human Layer"
    >
      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <ConsolePanel accent="accent" eyebrow="Mission / Why now" title="Our mission">
          <div className="grid gap-4 text-sm leading-7 text-muted-foreground">
            <p>
              In a network environment saturated with generative media and automated actors,
              proof of humanity becomes infrastructure rather than branding. Sui Human is
              designed to be that infrastructure.
            </p>
            <p>
              We want the client experience to feel technical, sovereign, and calm: a system
              that respects the user while still making strong, visible claims about trust.
            </p>
          </div>
        </ConsolePanel>

        <ConsolePanel accent="signal" eyebrow="Network / Reach" title="Node distribution">
          <div className="grid gap-4">
            <div className="grid min-h-64 place-items-center border border-line/50 bg-[radial-gradient(circle_at_center,rgba(0,85,255,0.12),transparent_42%),linear-gradient(135deg,rgba(0,212,255,0.08),transparent)]">
              <div className="grid gap-2 text-center">
                <p className="font-headline text-5xl font-black uppercase tracking-tight text-foreground">142</p>
                <p className="text-[0.68rem] uppercase tracking-[0.28em] text-muted-foreground">
                  Active oracles
                </p>
              </div>
            </div>
            <p className="text-sm leading-7 text-muted-foreground">
              A manuscript-style map block can live here later. For now, this preserves the
              intended asymmetry and data-heavy right column from the design reference.
            </p>
          </div>
        </ConsolePanel>
      </section>

      <ConsolePanel accent="neutral" eyebrow="Values / Doctrine" title="Core values">
        <div className="grid gap-4 lg:grid-cols-3">
          {values.map((value, index) => (
            <article
              className="border border-line/60 bg-background/60 p-5 transition hover:border-accent/60"
              key={value.title}
            >
              <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                00{index + 1}
              </p>
              <h3 className="mt-3 font-headline text-xl font-black uppercase tracking-tight text-foreground">
                {value.title}
              </h3>
              <p className="mt-4 text-sm leading-7 text-muted-foreground">{value.body}</p>
            </article>
          ))}
        </div>
      </ConsolePanel>

      <ConsolePanel
        accent="accent"
        description="The docs show this as a personnel wall. We can replace these placeholders with real team content later without changing the grid."
        eyebrow="System / Architects"
        title="Mission operators"
      >
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {team.map((member) => (
            <article className="border border-line/60 bg-background/60 p-4" key={member.name}>
              <div className="aspect-[4/5] border border-line/50 bg-[linear-gradient(135deg,rgba(0,85,255,0.18),transparent_55%),linear-gradient(180deg,rgba(0,0,0,0.04),transparent)]" />
              <div className="mt-4 grid gap-1">
                <h3 className="font-headline text-lg font-black uppercase tracking-tight text-foreground">
                  {member.name}
                </h3>
                <p className="text-[0.68rem] uppercase tracking-[0.24em] text-muted-foreground">
                  {member.role}
                </p>
              </div>
            </article>
          ))}
        </div>
      </ConsolePanel>
    </AppShell>
  );
}

import { AppShell } from "@/components/chrome/app-shell";
import { ConsolePanel } from "@/components/chrome/console-panel";

const processSteps = [
  {
    id: "01",
    title: "AI Liveness",
    body: "Real-time anti-spoofing evaluates challenge motion, depth cues, and passive attack signals before an attestation can advance.",
    list: ["Depth mapping", "Challenge-response", "Replay resistance"],
  },
  {
    id: "02",
    title: "Behavioral Analysis",
    body: "The verifier watches non-linear movement and pacing to separate authentic human responses from automated scripts and canned loops.",
    list: ["Entropy checks", "Latency distribution", "Signal consistency"],
  },
  {
    id: "03",
    title: "Proof Issuance",
    body: "Successful sessions hand off a clean result shape ready for wallet-oriented proof minting and application-level access control.",
    list: ["Wallet-ready result", "Proof reference", "Session continuity"],
  },
] as const;

const architectureCards = [
  {
    eyebrow: "Layer / Capture",
    title: "Human Pulse",
    body: "Camera, landmarks, and motion state stay close to the client so liveness feels immediate and privacy-preserving.",
  },
  {
    eyebrow: "Layer / Evaluation",
    title: "Verifier Core",
    body: "Session streaming, challenge progression, and anti-spoof checks run through the same contract-backed event surface.",
  },
  {
    eyebrow: "Layer / Delivery",
    title: "Result Handoff",
    body: "Verified, failed, spoof-oriented, and expired outcomes resolve into client-safe pages without admin telemetry leakage.",
  },
] as const;

export function OverviewPage() {
  return (
    <AppShell
      activeSection="overview"
      description="Sui Human turns liveness, anti-spoofing, and wallet-oriented trust into a sequence the product can actually ship. This page is the protocol skeleton: what the system does, where the signal comes from, and how the front end should feel before deeper logic lands."
      eyebrow="Protocol / Overview"
      meta={[
        { label: "Posture", value: "Wallet-ready" },
        { label: "Mode", value: "Client flow" },
        { label: "Network", value: "Sui native" },
      ]}
      title="Proof of Biological Integrity"
    >
      <section className="grid gap-px border border-line/60 bg-line/40 lg:grid-cols-3">
        {processSteps.map((step, index) => (
          <ConsolePanel
            accent={index === 1 ? "signal" : "accent"}
            className="border-0 bg-panel/95 shadow-none"
            eyebrow={`Step / ${step.id}`}
            key={step.id}
            title={step.title}
          >
            <p className="text-sm leading-7 text-muted-foreground">{step.body}</p>
            <ul className="mt-6 grid gap-2 text-[0.68rem] uppercase tracking-[0.24em] text-foreground">
              {step.list.map((item) => (
                <li className="border border-line/50 bg-background/60 px-3 py-2" key={item}>
                  {item}
                </li>
              ))}
            </ul>
          </ConsolePanel>
        ))}
      </section>

      <ConsolePanel
        accent="signal"
        description="Each module below is a front-end facing surface area we can flesh out incrementally after the skeleton phase."
        eyebrow="System / Architecture"
        title="Deployment Surfaces"
      >
        <div className="grid gap-4 lg:grid-cols-3">
          {architectureCards.map((card) => (
            <article className="border border-line/60 bg-background/60 p-5" key={card.title}>
              <p className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                {card.eyebrow}
              </p>
              <h3 className="mt-3 font-headline text-xl font-bold uppercase tracking-tight text-foreground">
                {card.title}
              </h3>
              <p className="mt-4 text-sm leading-7 text-muted-foreground">{card.body}</p>
            </article>
          ))}
        </div>
      </ConsolePanel>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <ConsolePanel
          accent="accent"
          eyebrow="Readiness / Build"
          title="What ships in the first UI pass"
        >
          <div className="grid gap-3 text-sm leading-7 text-muted-foreground">
            <p>
              Landing, overview, about, main app shell, verification, and result pages now
              share one visual language instead of feeling like separate experiments.
            </p>
            <p>
              The next phase can focus on real sequencing, session restoration, and wallet
              handoff because the navigation and screen hierarchy are already in place.
            </p>
          </div>
        </ConsolePanel>

        <ConsolePanel accent="neutral" eyebrow="Signals / Snapshot" title="Current north star">
          <div className="grid gap-3 text-[0.68rem] uppercase tracking-[0.24em] text-muted-foreground">
            <div className="border border-line/50 bg-background/60 px-3 py-3">No operator telemetry in public routes</div>
            <div className="border border-line/50 bg-background/60 px-3 py-3">Client-safe state machine for verify and result</div>
            <div className="border border-line/50 bg-background/60 px-3 py-3">Reusable shell for future wallet and proof flows</div>
          </div>
        </ConsolePanel>
      </section>
    </AppShell>
  );
}

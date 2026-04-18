import Link from "next/link";

const productPillars = [
  {
    title: "Active liveness",
    body: "Challenge-response checks with blink, turn, nod, and smile sequencing make replay attacks harder to pass.",
  },
  {
    title: "Passive anti-spoof",
    body: "Server-side anti-spoof scoring runs alongside the challenge flow to catch print, replay, and synthetic presentation attempts.",
  },
  {
    title: "Privacy-first pipeline",
    body: "The MVP is designed around verifier hardening first, with storage, encryption, and proof layers integrated only after the core signal quality is trustworthy.",
  },
];

const flowSteps = [
  "Open the verification flow and allow webcam access.",
  "Center your face and follow the live challenge prompts.",
  "Finalize the session and receive the verifier decision.",
];

export default function HomePage() {
  return (
    <main className="marketing-shell">
      <section className="marketing-hero">
        <div className="marketing-copy">
          <p className="eyebrow">SUI HUMAN / CLIENT SURFACE</p>
          <h1>Human verification for wallet-native experiences.</h1>
          <p className="marketing-lede">
            A product-facing shell for proof-of-human verification. The verifier combines
            active liveness, passive anti-spoofing, and server-side safety gates before
            any downstream privacy or proof layers are attached.
          </p>
          <div className="marketing-actions">
            <Link className="marketing-button is-primary" href="/admin">
              Launch verifier demo
            </Link>
            <a className="marketing-button is-secondary" href="#how-it-works">
              How it works
            </a>
          </div>
        </div>
        <div className="marketing-card">
          <p className="marketing-card-label">Current MVP posture</p>
          <ul className="marketing-list">
            <li>Sequence-based challenge verification</li>
            <li>Live face quality and landmark spot-check gates</li>
            <li>Passive anti-spoof with QA-oriented telemetry</li>
          </ul>
          <p className="marketing-caption">
            Internal testing and threshold tuning continue in the dedicated admin console.
          </p>
        </div>
      </section>

      <section className="marketing-section">
        <div className="marketing-section-header">
          <p className="eyebrow">Why It Matters</p>
          <h2>Designed to separate product UX from verifier diagnostics.</h2>
        </div>
        <div className="marketing-grid">
          {productPillars.map((pillar) => (
            <article className="marketing-panel" key={pillar.title}>
              <h3>{pillar.title}</h3>
              <p>{pillar.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section" id="how-it-works">
        <div className="marketing-section-header">
          <p className="eyebrow">Main Flow</p>
          <h2>Simple client-facing journey.</h2>
        </div>
        <div className="flow-strip">
          {flowSteps.map((step, index) => (
            <article className="flow-step" key={step}>
              <span>{`0${index + 1}`}</span>
              <p>{step}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section marketing-trust">
        <div className="marketing-panel">
          <p className="eyebrow">Trust + Privacy</p>
          <h2>Raw verification quality comes first.</h2>
          <p>
            The current phase focuses on verifier reliability, challenge hardening, and
            attack resistance. That means the user-facing shell stays clean while the
            diagnostic console remains available for calibration and release QA.
          </p>
        </div>
        <div className="marketing-panel">
          <p className="eyebrow">Internal Console</p>
          <h2>Admin page for engineering and testing.</h2>
          <p>
            Engineers and testers use the admin route to inspect face quality, landmark
            spot-checks, motion continuity, anti-spoof scores, and attack-mode session
            results without exposing those details in the public-facing UI.
          </p>
          <Link className="marketing-inline-link" href="/admin">
            Open admin / testing console
          </Link>
        </div>
      </section>
    </main>
  );
}

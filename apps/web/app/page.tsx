import { CapabilitiesSection } from "@/components/marketing/capabilities-section";
import { FinalCtaSection } from "@/components/marketing/final-cta-section";
import { HeroSection } from "@/components/marketing/hero-section";
import { ProcessSection } from "@/components/marketing/process-section";
import { SiteHeader } from "@/components/marketing/site-header";
import { TrustSection } from "@/components/marketing/trust-section";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <SiteHeader />
      <HeroSection />
      <CapabilitiesSection />
      <ProcessSection />
      <TrustSection />
      <FinalCtaSection />
    </main>
  );
}

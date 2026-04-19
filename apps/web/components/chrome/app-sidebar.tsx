import Link from "next/link";
import { LaunchVerificationButton } from "@/components/verification/launch-verification-button";

export type AppSection = "main_app" | "overview" | "about" | "admin";

const navItems: Array<{ href: string; id: AppSection; label: string; meta: string }> = [
  { href: "/app", id: "main_app", label: "TERMINAL", meta: "MAIN_APP" },
  { href: "/overview", id: "overview", label: "OVERVIEW", meta: "PROTOCOL" },
  { href: "/about", id: "about", label: "MISSION", meta: "ORIGIN" },
  { href: "/admin", id: "admin", label: "QA_CONSOLE", meta: "INTERNAL" },
];

export function AppSidebar(props: { activeSection: AppSection }) {
  return (
    <aside className="fixed left-0 top-[73px] hidden h-[calc(100svh-73px)] w-64 flex-col justify-between border-r border-line/60 bg-surface/95 px-4 py-6 md:flex">
      <div className="space-y-6">
        <div className="border border-line/60 bg-panel/80 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center border border-accent/40 bg-background text-xs font-black uppercase tracking-[0.3em] text-accent">
              01
            </div>
            <div>
              <p className="font-headline text-sm font-black uppercase tracking-tight text-foreground">
                Operator_01
              </p>
              <p className="text-[0.6rem] uppercase tracking-[0.28em] text-muted-foreground">
                Identity verified
              </p>
            </div>
          </div>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => {
            const isActive = item.id === props.activeSection;
            return (
              <Link
                className={`flex items-center justify-between border px-4 py-3 text-[0.68rem] uppercase tracking-[0.24em] transition ${
                  isActive
                    ? "border-accent/60 bg-panel text-foreground"
                    : "border-transparent bg-transparent text-muted-foreground hover:border-line/60 hover:bg-panel/70 hover:text-foreground"
                }`}
                href={item.href}
                key={item.href}
              >
                <span>{item.label}</span>
                <span className={isActive ? "text-accent" : "text-muted-foreground"}>{item.meta}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="space-y-4 border-t border-line/60 pt-5">
        <LaunchVerificationButton className="w-full" label="Initiate scan" variant="secondary" />
        <div className="grid gap-2 text-[0.62rem] uppercase tracking-[0.22em] text-muted-foreground">
          <Link className="transition hover:text-accent" href="/">
            Start flow
          </Link>
          <Link className="transition hover:text-accent" href="/overview">
            Protocol docs
          </Link>
        </div>
      </div>
    </aside>
  );
}

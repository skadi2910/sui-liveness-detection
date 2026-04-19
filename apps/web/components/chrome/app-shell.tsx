import type { ReactNode } from "react";
import { SiteHeader } from "@/components/marketing/site-header";
import { AppSidebar, type AppSection } from "./app-sidebar";

type MetaItem = {
  label: string;
  value: string;
};

export function AppShell(props: {
  activeSection: AppSection;
  aside?: ReactNode;
  children: ReactNode;
  description: string;
  eyebrow: string;
  meta?: MetaItem[];
  title: string;
}) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="pointer-events-none fixed inset-0 opacity-[0.08] scanlines" />
      <SiteHeader compact />
      <AppSidebar activeSection={props.activeSection} />

      <main className="px-4 pb-16 pt-8 md:pl-72 md:pr-8">
        <div className="mx-auto max-w-7xl space-y-8">
          <section className="relative overflow-hidden border border-line/70 bg-panel/90 p-6 shadow-panel sm:p-8 lg:p-10">
            <div className="absolute right-0 top-0 hidden h-full w-32 bg-[linear-gradient(180deg,rgba(var(--accent),0.16),transparent)] lg:block" />
            <div className="relative max-w-4xl">
              <p className="text-[0.68rem] uppercase tracking-[0.32em] text-accent">{props.eyebrow}</p>
              <h1 className="mt-4 font-headline text-4xl font-black uppercase tracking-tight text-foreground sm:text-6xl lg:text-7xl">
                {props.title}
              </h1>
              <p className="mt-5 max-w-2xl border-l-2 border-accent pl-5 text-sm leading-7 text-muted-foreground sm:text-base">
                {props.description}
              </p>
            </div>

            {props.meta?.length ? (
              <dl className="relative mt-8 grid gap-3 border border-line/60 bg-background/60 p-4 sm:grid-cols-3">
                {props.meta.map((item) => (
                  <div className="grid gap-1" key={item.label}>
                    <dt className="text-[0.62rem] uppercase tracking-[0.24em] text-muted-foreground">
                      {item.label}
                    </dt>
                    <dd className="font-headline text-xl font-bold uppercase tracking-tight text-foreground">
                      {item.value}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </section>

          {props.aside ? (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_21rem]">
              <div className="space-y-6">{props.children}</div>
              <aside className="space-y-6">{props.aside}</aside>
            </div>
          ) : (
            <div className="space-y-6">{props.children}</div>
          )}
        </div>
      </main>
    </div>
  );
}

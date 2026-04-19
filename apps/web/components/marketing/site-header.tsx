"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { WalletButtonSlot } from "@/components/wallet/wallet-button-slot";

const navItems = [
  { href: "/", label: "Home" },
  { href: "/overview", label: "Overview" },
  { href: "/about", label: "About" },
  { href: "/app", label: "App" },
] as const;

export function SiteHeader(props: {
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <header className="sticky top-0 z-50 border-b border-line/70 bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link
            className="font-headline text-lg font-black uppercase tracking-tight text-foreground sm:text-xl"
            href="/"
          >
            SUI_HUMAN
          </Link>
          <nav
            className={`hidden items-center text-muted-foreground md:flex ${
              props.compact
                ? "gap-4 text-[0.64rem] uppercase tracking-[0.22em]"
                : "gap-6 text-[0.7rem] uppercase tracking-[0.28em]"
            }`}
          >
            {navItems.map((item) => (
              <Link className="transition hover:text-accent" href={item.href} key={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <Link
            className="hidden border border-line px-3 py-2 text-[0.65rem] uppercase tracking-[0.24em] text-muted-foreground transition hover:border-accent hover:text-foreground sm:inline-flex"
            href="/admin"
          >
            Admin
          </Link>
          <WalletButtonSlot />
          <ThemeToggle />
          {props.action}
        </div>
      </div>
    </header>
  );
}

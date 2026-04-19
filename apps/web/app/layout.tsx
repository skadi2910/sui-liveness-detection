import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";
import { ThemeProvider, themeInitScript } from "@/components/theme/theme-provider";
import { SuiWalletProvider } from "@/components/wallet/sui-wallet-provider";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "Sui Human",
  description: "Client-facing verification flow and admin QA console for Sui Human.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html
      className={`${spaceGrotesk.variable} ${jetbrainsMono.variable}`}
      data-theme="light"
      lang="en"
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-background font-mono text-foreground antialiased">
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <ThemeProvider>
          <SuiWalletProvider>{children}</SuiWalletProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}

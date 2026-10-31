import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { formatDate, getMeta } from "@/lib/data";
import "./globals.css";

// globals.css maps Tailwind's font-sans to --font-sans, so the variable must use that name.
const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "The Research Roundup",
  description: "Monthly digest of new economics research for Global Markets, with an explorer of every screened paper.",
};

const NAV = [
  { href: "/", label: "Issues" },
  { href: "/papers/", label: "Papers" },
  { href: "/sources/", label: "Sources" },
  { href: "/methodology/", label: "Methodology" },
];

export default function RootLayout({ children }: LayoutProps<"/">) {
  const meta = getMeta();
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background">
        <header className="border-b bg-[#0b2545] text-white">
          <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-4">
            <Link href="/" className="font-serif text-xl font-bold tracking-tight">
              The Research Roundup
            </Link>
            <nav className="flex gap-5 text-sm text-slate-300">
              {NAV.map((item) => (
                <Link key={item.href} href={item.href} className="hover:text-white">
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t">
          <div className="mx-auto flex w-full max-w-6xl flex-wrap justify-between gap-2 px-4 py-6 text-xs text-muted-foreground">
            <span>
              New economics research for Global Markets, screened and summarised automatically from titles and abstracts.
            </span>
            {meta && (
              <span>
                {meta.papers_screened} papers screened from {meta.sources_enabled} sources · data updated{" "}
                {formatDate(meta.generated_at.slice(0, 10))}
              </span>
            )}
          </div>
        </footer>
      </body>
    </html>
  );
}

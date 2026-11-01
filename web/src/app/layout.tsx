import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { formatDate, getMeta } from "@/lib/data";

import "./globals.css";

import Navbar from "@/components/navbar";
import Footer from "@/components/footer";

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
  description:
    "Monthly digest of new economics research for Global Markets, with an explorer of every screened paper.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  const meta = getMeta();
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background">
        <Navbar />
        <main className="w-full max-w-6xl mx-auto py-12 flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}

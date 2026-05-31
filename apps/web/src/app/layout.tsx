import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Inter } from "next/font/google";
import "./globals.css";

// Dark Electric typography (rebrand 2026-05-31): Geist Sans headings + Inter
// body + Geist Mono code. GeistSans/GeistMono expose --font-geist-sans /
// --font-geist-mono; Inter is mapped to --font-inter. tailwind.config.ts
// fontFamily reads these var names. Replaces DM Serif / DM Sans / JetBrains.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://smarttap.ie"),
  title: {
    default: "SmartTap — One tap. Reviews go up. Regulars come back.",
    template: "%s · SmartTap",
  },
  description:
    "The only loyalty and reviews system for Dublin businesses where the data, the customer, and the stand on your counter belong to you. From €29/month. No app required.",
  applicationName: "SmartTap",
  keywords: [
    "loyalty stand Dublin",
    "Google Reviews NFC",
    "barber loyalty card",
    "café review stand",
    "GDPR loyalty Ireland",
    "no-app loyalty",
  ],
  authors: [{ name: "Henrique Pasquetto", url: "https://smarttap.ie" }],
  creator: "Henrique Pasquetto",
  publisher: "SmartTap",
  openGraph: {
    title: "SmartTap — Loyalty and reviews for Dublin businesses",
    description:
      "One tap on the counter. Stamps go up. Reviews go up. Regulars come back. Built in Dublin.",
    type: "website",
    locale: "en_IE",
    siteName: "SmartTap",
    url: "https://smarttap.ie",
  },
  twitter: {
    card: "summary_large_image",
    title: "SmartTap — Loyalty + reviews, built in Dublin",
    description:
      "One tap on the counter. Stamps go up. Reviews go up. Regulars come back.",
  },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico" },
    ],
    apple: "/apple-touch-icon.png",
  },
  formatDetection: {
    telephone: false,
    email: false,
    address: false,
  },
};

export const viewport = {
  // Dark-mode chrome now matches the Dark Electric base. Light kept for the
  // surfaces not yet migrated (dashboard, /t, etc). The landing overrides
  // this with a fixed dark theme-color in its own (landing)/layout viewport.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F5F0" },
    { media: "(prefers-color-scheme: dark)", color: "#0A0A0F" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable} ${inter.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}

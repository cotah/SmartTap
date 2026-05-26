import type { Metadata } from "next";
import { DM_Serif_Display, DM_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const dmSerif = DM_Serif_Display({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
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
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F7F5F0" },
    { media: "(prefers-color-scheme: dark)", color: "#1B4D3E" },
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
      className={`${dmSerif.variable} ${dmSans.variable} ${jetbrains.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}

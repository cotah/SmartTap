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
  openGraph: {
    title: "SmartTap — Loyalty and reviews for Dublin businesses",
    description:
      "One tap on the counter. Stamps go up. Reviews go up. Regulars come back. Built in Dublin.",
    type: "website",
    locale: "en_IE",
  },
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

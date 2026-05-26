import type { Metadata } from "next";

import { LegalStub } from "../(legal)/_components/stub-page";

export const metadata: Metadata = {
  title: "GDPR",
  description:
    "How SmartTap helps your shop stay GDPR-compliant by default — explicit consent, EU hosting, full data export.",
};

export default function GdprPage() {
  return (
    <LegalStub
      title="GDPR, built in"
      description="SmartTap is designed to make a small Irish shop GDPR-compliant by default. The summary below is the working ruleset; the formal page lands in the next sprint."
      outline={[
        "Customers opt in explicitly before any contact details are collected. No pre-ticked boxes, no hidden checkboxes.",
        "Customers can unsubscribe from any WhatsApp / email via a one-tap link — and that preference is remembered across shops.",
        "We act as a data processor for your shop; you remain the data controller. The dashboard exposes every record we hold.",
        "All data is hosted in the EU (Supabase Frankfurt). No data leaves the EEA without your explicit instruction.",
        "Subject-access and deletion requests can be served end-to-end from the dashboard in under five minutes.",
        "Our DPA template, ready to sign, will be linked here once final.",
      ]}
    />
  );
}

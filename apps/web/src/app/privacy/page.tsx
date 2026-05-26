import type { Metadata } from "next";

import { LegalStub } from "../(legal)/_components/stub-page";

export const metadata: Metadata = {
  title: "Privacy",
  description:
    "SmartTap privacy policy — what we collect, why we collect it, where we host it, and how long we keep it. EU-hosted, GDPR-compliant.",
};

export default function PrivacyPage() {
  return (
    <LegalStub
      title="Privacy policy"
      description="Full draft from our Irish solicitor lands here in the next sprint. Until then the short version is below."
      outline={[
        "What data we collect when a customer taps a SmartTap stand (and what we don't).",
        "Where the data is hosted — EU only, never outside the EEA.",
        "How long we keep customer records and how you (the shop) can delete them at any time.",
        "Subprocessors we use to run the service — Stripe (billing), Resend (email), Twilio (WhatsApp), Supabase (database).",
        "Your customers' GDPR rights and how to exercise them through the dashboard.",
      ]}
    />
  );
}

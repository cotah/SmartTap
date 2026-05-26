import type { Metadata } from "next";

import { LegalStub } from "../(legal)/_components/stub-page";

export const metadata: Metadata = {
  title: "Terms",
  description:
    "SmartTap terms of service — the agreement between SmartTap and the businesses using it.",
};

export default function TermsPage() {
  return (
    <LegalStub
      title="Terms of service"
      description="Our Irish solicitor is drafting the full version. The principles below are what we already operate by."
      outline={[
        "30-day free trial. No credit card required to start.",
        "No long-term contracts. Cancel from your dashboard at any time, with no notice period.",
        "Setup fee is non-refundable once the stand is shipped — we'll always tell you the ship date before charging.",
        "Subscription pricing is locked at the level you signed up on. Founding-member rate is yours for life.",
        "Your customer data is yours. Export is one click; deletion is two.",
        "Limits, refunds, liability, governing law (Republic of Ireland).",
      ]}
    />
  );
}

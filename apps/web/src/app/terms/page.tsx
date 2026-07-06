import type { Metadata } from "next";

import {
  LegalList,
  LegalPage,
  LegalSection,
  LegalText,
} from "../(legal)/_components/legal-page";

export const metadata: Metadata = {
  title: "Terms",
  description:
    "SmartTap terms of service — the agreement between SmartTap and the businesses using it.",
};

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of service"
      intro="The agreement between SmartTap and the businesses that use it. Short on purpose — these are the rules we actually operate by."
      updated="6 July 2026"
    >
      <LegalSection title="The service">
        <LegalText>
          SmartTap provides a physical NFC stand plus a software platform for
          collecting Google reviews, running a digital loyalty programme, and
          messaging your customers — operated by Henrique Pasquetto, Dublin,
          Ireland. By creating an account you agree to these terms.
        </LegalText>
      </LegalSection>

      <LegalSection title="Trial, billing and cancellation">
        <LegalList
          items={[
            "Every plan starts with a 30-day free trial. No credit card is required to start.",
            "Subscriptions are billed monthly (or annually, with two months free) through Stripe, in euro, at the price shown at signup.",
            "Your subscription price is locked at the level you signed up on. If you're on a founding-member rate, it's yours for as long as you keep the subscription.",
            "No long-term contracts. Cancel from your dashboard at any time — access runs to the end of the paid period, and no further charges are made.",
            "The one-time setup fee covers your custom-printed stand and onboarding. It's non-refundable once the stand has shipped — we always confirm the ship date before charging.",
          ]}
        />
      </LegalSection>

      <LegalSection title="The stand (hardware)">
        <LegalList
          items={[
            "The stand is yours — it's covered by the setup fee, not rented.",
            "If a stand arrives damaged or its NFC tag fails within 12 months of normal use, we replace it free of charge.",
            "The stand only works with an active SmartTap subscription; the NFC link points at our platform.",
          ]}
        />
      </LegalSection>

      <LegalSection title="Your data, your customers">
        <LegalList
          items={[
            "Customer data collected through your stand belongs to your business. We process it on your behalf (see the Privacy policy for the controller/processor split).",
            "Export is one click from the dashboard (CSV). Deleting a customer record is immediate.",
            "If you cancel, you can export everything first. We delete your tenant data after closure, subject to legal retention obligations.",
            "You're responsible for using the messaging features lawfully — only contact customers who opted in, and honour unsubscribes. SmartTap enforces consent flags automatically, but the messages you send are yours.",
          ]}
        />
      </LegalSection>

      <LegalSection title="Fair use">
        <LegalList
          items={[
            "Don't use SmartTap to send spam, mislead customers, or incentivise fake reviews. Google's review policies apply — we help you ask happy customers for honest reviews, nothing else.",
            "Don't attempt to break, overload, or reverse-engineer the service.",
            "Plan limits (customer counts per plan) are shown on the pricing page; we'll tell you well before you hit one.",
          ]}
        />
      </LegalSection>

      <LegalSection title="Service availability and liability">
        <LegalList
          items={[
            "We run SmartTap on reputable EU infrastructure and aim for it to be available around the clock, but we don't guarantee uninterrupted service.",
            "To the extent permitted by law, our total liability under these terms is capped at the fees you paid us in the 12 months before the claim.",
            "We're not liable for indirect losses (lost profits, lost reviews, lost custom).",
          ]}
        />
      </LegalSection>

      <LegalSection title="Changes and governing law">
        <LegalList
          items={[
            "If we change these terms in a way that affects you materially, we'll email you at least 14 days before it takes effect.",
            "These terms are governed by the laws of the Republic of Ireland, and the Irish courts have jurisdiction.",
          ]}
        />
      </LegalSection>
    </LegalPage>
  );
}

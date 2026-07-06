import type { Metadata } from "next";

import {
  LegalList,
  LegalPage,
  LegalSection,
  LegalText,
} from "../(legal)/_components/legal-page";

export const metadata: Metadata = {
  title: "GDPR",
  description:
    "How SmartTap helps your shop stay GDPR-compliant by default — explicit consent, EU hosting, full data export.",
};

export default function GdprPage() {
  return (
    <LegalPage
      title="GDPR, built in"
      intro="SmartTap is designed so a small Irish shop is GDPR-compliant by default — not as an afterthought you have to configure."
      updated="6 July 2026"
    >
      <LegalSection title="Consent first, always">
        <LegalList
          items={[
            "Customers opt in explicitly before any contact details are collected. No pre-ticked boxes, no hidden checkboxes, no 'by tapping you agree' tricks.",
            "A tap without the join form is completely anonymous — we record that a tap happened, nothing about who tapped.",
            "Every message a customer can receive traces back to a consent they gave, with a timestamp we keep on record.",
            "Opting out is one tap, honoured immediately and automatically — the platform won't let a shop message someone who withdrew consent.",
          ]}
        />
      </LegalSection>

      <LegalSection title="You're the controller, we're the processor">
        <LegalText>
          Your shop decides why customer data is collected (your loyalty
          programme); SmartTap processes it on your instructions. The
          dashboard exposes every record we hold for your business — nothing
          is hidden in our systems that you can&apos;t see, export or delete
          yourself.
        </LegalText>
        <LegalText>
          A signed data processing agreement (DPA) is available to any
          customer on request — email{" "}
          <a
            href="mailto:support@smarttap.ie"
            className="text-electric-cyan underline-offset-4 hover:underline"
          >
            support@smarttap.ie
          </a>
          .
        </LegalText>
      </LegalSection>

      <LegalSection title="Data stays in the EU">
        <LegalList
          items={[
            "The database runs on Supabase in AWS eu-west-1 — Ireland. Customer records don't leave the EU in normal operation.",
            "Analytics are EU-hosted (PostHog EU). Where a subprocessor operates globally, transfers are covered by EU Standard Contractual Clauses — the full list is in the Privacy policy.",
          ]}
        />
      </LegalSection>

      <LegalSection title="Subject requests, served in minutes">
        <LegalList
          items={[
            "Access request: the customer's full record is visible in your dashboard, exportable as CSV in one click.",
            "Deletion request: two clicks in the dashboard, effective immediately.",
            "If a customer contacts us directly instead of you, we'll handle it and let you know.",
          ]}
        />
      </LegalSection>

      <LegalSection title="Data minimisation by design">
        <LegalList
          items={[
            "We only ask customers for what the loyalty programme needs: a contact method and a name. Birthday is optional.",
            "Card details never touch SmartTap — billing runs entirely inside Stripe.",
            "One-time SMS codes are stored hashed and expire after 10 minutes.",
            "Phone numbers used for account recovery are used for the code only — never added to any marketing list.",
          ]}
        />
      </LegalSection>

      <LegalSection title="Want the detail?">
        <LegalText>
          The full picture — every subprocessor, retention windows, legal
          bases — is in the{" "}
          <a
            href="/privacy"
            className="text-electric-cyan underline-offset-4 hover:underline"
          >
            Privacy policy
          </a>
          . If you have a question it doesn&apos;t answer, email us and a
          human (the founder) replies.
        </LegalText>
      </LegalSection>
    </LegalPage>
  );
}

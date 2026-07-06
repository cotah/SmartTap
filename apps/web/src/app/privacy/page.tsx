import type { Metadata } from "next";

import {
  LegalList,
  LegalPage,
  LegalSection,
  LegalTable,
  LegalText,
} from "../(legal)/_components/legal-page";

export const metadata: Metadata = {
  title: "Privacy",
  description:
    "SmartTap privacy policy — what we collect, why we collect it, where we host it, and how long we keep it. EU-hosted, GDPR-compliant.",
};

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy policy"
      intro="Plain English, no legalese-for-the-sake-of-it. This is what SmartTap collects, why, where it lives, and how to get it removed."
      updated="6 July 2026"
    >
      <LegalSection title="Who we are">
        <LegalText>
          SmartTap (smarttap.ie) is operated by Henrique Pasquetto, based in
          Dublin, Ireland. For anything privacy-related, email{" "}
          <a
            href="mailto:support@smarttap.ie"
            className="text-electric-cyan underline-offset-4 hover:underline"
          >
            support@smarttap.ie
          </a>
          .
        </LegalText>
        <LegalText>
          SmartTap wears two hats under GDPR, and it matters which one applies
          to you:
        </LegalText>
        <LegalList
          items={[
            <>
              <strong className="text-electric-text">
                If you run a business on SmartTap
              </strong>{" "}
              — we are the data controller for your account (your name, email,
              business details, billing).
            </>,
            <>
              <strong className="text-electric-text">
                If you tapped a SmartTap stand in a shop
              </strong>{" "}
              — the shop is the data controller and we are its data processor.
              We only hold your details on the shop&apos;s behalf and on its
              instructions. Requests about your data can go to the shop or
              directly to us — either works.
            </>,
          ]}
        />
      </LegalSection>

      <LegalSection title="What we collect">
        <LegalText>
          <strong className="text-electric-text">
            When a customer taps a stand:
          </strong>{" "}
          the tap itself (which stand, when, device type). That&apos;s it — a
          tap alone is anonymous. Contact details (phone or email, name,
          optionally a birthday) are only stored if the customer fills in the
          join form and ticks the consent box. No pre-ticked boxes, no
          collection in the background.
        </LegalText>
        <LegalText>
          <strong className="text-electric-text">
            For business accounts:
          </strong>{" "}
          name, email, business name and type, Google review link, and billing
          details (card data is held by Stripe — it never touches our
          servers).
        </LegalText>
        <LegalText>
          <strong className="text-electric-text">On this website:</strong>{" "}
          anonymous product analytics (PostHog, hosted in the EU) and error
          reports (Sentry). No advertising trackers, no data sold to anyone,
          ever.
        </LegalText>
      </LegalSection>

      <LegalSection title="Why we collect it (legal bases)">
        <LegalList
          items={[
            <>
              <strong className="text-electric-text">Consent</strong> — a
              customer&apos;s contact details and any messages the shop sends
              them (loyalty updates, review reminders). Withdrawable at any
              time, one tap.
            </>,
            <>
              <strong className="text-electric-text">Contract</strong> —
              running the service for businesses: accounts, billing,
              transactional email.
            </>,
            <>
              <strong className="text-electric-text">
                Legitimate interest
              </strong>{" "}
              — keeping the service secure and working: rate-limiting, fraud
              prevention, error logs, anonymous usage analytics.
            </>,
          ]}
        />
      </LegalSection>

      <LegalSection title="Where the data lives">
        <LegalText>
          The database runs on Supabase in AWS <em>eu-west-1</em> — that&apos;s
          Ireland. Customer records never leave the EU as part of normal
          operation. A small number of subprocessors below operate globally;
          where data leaves the EEA it is covered by EU Standard Contractual
          Clauses.
        </LegalText>
      </LegalSection>

      <LegalSection title="Subprocessors we use">
        <LegalTable
          rows={[
            {
              name: "Supabase",
              detail:
                "Database and authentication. Hosted in AWS eu-west-1 (Ireland).",
            },
            {
              name: "Vercel",
              detail: "Hosts this website and the dashboard.",
            },
            {
              name: "Railway",
              detail: "Hosts the SmartTap API.",
            },
            {
              name: "Stripe",
              detail:
                "Subscription billing for businesses. Card details are stored by Stripe only.",
            },
            {
              name: "Resend",
              detail:
                "Transactional email — receipts, reports, thank-you notes.",
            },
            {
              name: "Twilio",
              detail:
                "SMS delivery of one-time verification codes (account recovery). Phone numbers are used for the code only — never added to any marketing list.",
            },
            {
              name: "Meta (WhatsApp)",
              detail:
                "WhatsApp message delivery — the owner assistant, and review reminders to customers who opted in.",
            },
            {
              name: "Anthropic",
              detail:
                "AI drafting — turns a shop's questions and public review text into draft answers. Not used to train AI models.",
            },
            {
              name: "Google",
              detail:
                "Business Profile integration — reads a shop's public reviews when the shop connects its Google account.",
            },
            {
              name: "PostHog (EU)",
              detail: "Anonymous product analytics, hosted in the EU.",
            },
            {
              name: "Sentry",
              detail: "Error reporting so we can fix bugs quickly.",
            },
          ]}
        />
      </LegalSection>

      <LegalSection title="How long we keep it">
        <LegalList
          items={[
            "Customer loyalty records: for as long as the shop uses SmartTap. Shops can delete any customer record from the dashboard at any time; deletion is immediate.",
            "SMS verification codes: stored hashed, expire after 10 minutes.",
            "Business account data: for the life of the account, then removed after closure once billing/tax obligations allow.",
            "Error logs and analytics: automatically expire on the providers' standard retention windows (typically 90 days).",
          ]}
        />
      </LegalSection>

      <LegalSection title="Cookies">
        <LegalText>
          We use essential cookies only: a session cookie on the loyalty page
          so a returning customer keeps their stamps, and login cookies on the
          business dashboard. No third-party advertising cookies.
        </LegalText>
      </LegalSection>

      <LegalSection title="Your rights">
        <LegalText>
          Under GDPR you can ask for access, correction, deletion, a portable
          copy, or restriction of your data — whether you&apos;re a business
          or a customer who tapped a stand. Email{" "}
          <a
            href="mailto:support@smarttap.ie"
            className="text-electric-cyan underline-offset-4 hover:underline"
          >
            support@smarttap.ie
          </a>{" "}
          and we&apos;ll respond within 30 days (usually much faster). If
          you&apos;re unhappy with how we handle it, you can complain to the
          Irish Data Protection Commission (dataprotection.ie).
        </LegalText>
      </LegalSection>
    </LegalPage>
  );
}

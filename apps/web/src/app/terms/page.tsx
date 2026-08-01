import type { Metadata } from "next";
import Link from "next/link";

import {
  LegalList,
  LegalPage,
  LegalSection,
  LegalText,
} from "../(legal)/_components/legal-page";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "SmartTap terms of service — the agreement between SmartTap (operated by Henrique Pasquetto, trading as Capivarex, Dublin, Ireland) and the businesses using it.",
};

const linkClass = "text-electric-cyan underline-offset-4 hover:underline";

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      intro="The agreement between SmartTap and the businesses that use it."
      updated="29 July 2026"
    >
      <LegalSection title="Who provides the service">
        <LegalText>
          These Terms of Service (&quot;Terms&quot;) govern your use of
          SmartTap, a service operated by{" "}
          <strong className="text-electric-text">Henrique Pasquetto</strong>, a
          sole trader established in Ireland, trading as{" "}
          <strong className="text-electric-text">Capivarex</strong> (registered
          business name no.{" "}
          <strong className="text-electric-text">787229</strong>), of 46
          Leinster Road, Rathmines, Dublin D06 R6K1, Ireland
          (&quot;SmartTap&quot;, &quot;we&quot;, &quot;us&quot;,
          &quot;our&quot;).
        </LegalText>
        <LegalText>
          By subscribing to or using SmartTap, you (&quot;Customer&quot;,
          &quot;you&quot;) agree to these Terms. If you do not agree, do not
          use the service.
        </LegalText>
      </LegalSection>

      <LegalSection title="1. The service">
        <LegalText>
          SmartTap provides tools and services for small businesses, which may
          include:
        </LegalText>
        <LegalList
          items={[
            <>
              <strong className="text-electric-text">
                NFC tags and physical hardware
              </strong>{" "}
              placed in your premises, linking customers to your digital menu,
              loyalty programme or review page.
            </>,
            <>
              <strong className="text-electric-text">
                Digital menu pages
              </strong>{" "}
              hosted at <code>smarttap.ie/menu/[your-business]</code>.
            </>,
            <>
              <strong className="text-electric-text">
                AI-assisted review responses
              </strong>
              , where SmartTap generates draft replies to reviews left on your
              Google Business Profile.
            </>,
            <>
              <strong className="text-electric-text">
                Messaging automation
              </strong>{" "}
              for connected social media accounts.
            </>,
            <>
              <strong className="text-electric-text">
                Loyalty programme tools
              </strong>
              , including digital stamps and rewards.
            </>,
          ]}
        />
        <LegalText>
          Not all features are enabled for every Customer. The features
          included in your subscription are those agreed at the time of
          purchase.
        </LegalText>
      </LegalSection>

      <LegalSection title="2. Eligibility and accounts">
        <LegalText>
          You must be at least 18 years old and authorised to enter into
          agreements on behalf of the business you represent.
        </LegalText>
        <LegalText>
          Where SmartTap manages your account on your behalf, you remain
          responsible for the accuracy of the information you provide to us
          and for the commitments made in your business&apos;s name.
        </LegalText>
      </LegalSection>

      <LegalSection title="3. Access to third-party accounts">
        <LegalText>
          To deliver certain features, you may grant SmartTap access to
          accounts you control on third-party platforms, including Google
          Business Profile.
        </LegalText>
        <LegalText>By granting this access, you confirm that:</LegalText>
        <LegalList
          items={[
            "You own, or are authorised to administer, those accounts.",
            "You have the authority to permit SmartTap to act on your behalf within them.",
            "You will inform us promptly if that authority changes or is withdrawn.",
          ]}
        />
        <LegalText>
          You may revoke this access at any time through the relevant
          platform. Doing so will disable the affected features, and we may be
          unable to continue providing part or all of the service.
        </LegalText>
      </LegalSection>

      <LegalSection title="4. AI-generated content">
        <LegalText>
          Some SmartTap features use artificial intelligence to generate draft
          text, such as replies to customer reviews or messages.
        </LegalText>
        <LegalText>You acknowledge that:</LegalText>
        <LegalList
          items={[
            <>
              AI-generated content is a{" "}
              <strong className="text-electric-text">draft</strong> and may
              contain errors, inaccuracies or inappropriate wording.
            </>,
            "Where content is published on your behalf, it is published in your business's name and you remain responsible for it.",
            "We do not guarantee that generated content will be accurate, suitable, or free from error.",
            "You may request changes to how content is generated for your business, and may request that automated publication be disabled at any time.",
          ]}
        />
        <LegalText>
          Where automated publication is enabled for your account, you have
          expressly agreed to content being published without individual prior
          review.
        </LegalText>
      </LegalSection>

      <LegalSection title="5. Your responsibilities">
        <LegalText>You agree:</LegalText>
        <LegalList
          items={[
            "To provide accurate and up-to-date information about your business, including menus, opening hours and pricing.",
            "Not to use SmartTap for any unlawful purpose, or to publish content that is defamatory, misleading, discriminatory or otherwise unlawful.",
            "To comply with the terms of any third-party platform connected to your account, including Google and Meta platform policies.",
            "To hold all rights necessary in any content you supply to us, including images, logos and menu content.",
          ]}
        />
      </LegalSection>

      <LegalSection title="6. Third-party platforms">
        <LegalText>
          SmartTap relies on services operated by third parties, including
          Google and Meta. We do not control those platforms.
        </LegalText>
        <LegalText>
          Changes to their policies, pricing, availability or approval
          processes may affect or interrupt SmartTap features. Where a feature
          depends on approval or continued access from a third party, we do
          not guarantee that such approval will be granted or maintained.
        </LegalText>
        <LegalText>
          We will inform you where a change materially affects the service you
          receive.
        </LegalText>
      </LegalSection>

      <LegalSection title="7. Fees, billing and trials">
        <LegalText>
          Fees, billing frequency and any trial period are those agreed at the
          time of purchase.
        </LegalText>
        <LegalText>
          Payments are processed by our payment provider. Unless stated
          otherwise, fees are payable in advance and are non-refundable for
          the period already invoiced.
        </LegalText>
        <LegalText>
          We may change our fees on{" "}
          <strong className="text-electric-text">
            30 days&apos; written notice
          </strong>
          . If you do not accept a change, you may cancel before it takes
          effect.
        </LegalText>
        <LegalText>
          Physical hardware supplied to you (including NFC tags and stands)
          remains subject to any separate purchase terms agreed at the time of
          sale.
        </LegalText>
      </LegalSection>

      <LegalSection title="8. Term, suspension and termination">
        <LegalText>
          These Terms apply for as long as you use the service.
        </LegalText>
        <LegalText>
          <strong className="text-electric-text">You may cancel</strong> at
          any time with effect from the end of your current billing period.
        </LegalText>
        <LegalText>
          <strong className="text-electric-text">
            We may suspend or terminate
          </strong>{" "}
          your access if:
        </LegalText>
        <LegalList
          items={[
            "You breach these Terms and, where the breach can be remedied, do not remedy it within 14 days of being asked;",
            "Payment is overdue;",
            "Continuing to provide the service would place us in breach of a third-party platform's policies or of applicable law.",
          ]}
        />
        <LegalText>
          On termination, we will cease providing the service. Data retention
          following termination is described in our Privacy Policy and in our
          Data Deletion policy.
        </LegalText>
      </LegalSection>

      <LegalSection title="9. Data protection">
        <LegalText>
          Our handling of personal data is described in our{" "}
          <Link href="/privacy" className={linkClass}>
            Privacy Policy
          </Link>
          .
        </LegalText>
        <LegalText>
          Where we process personal data on your behalf in the course of
          providing the service, you act as data controller and we act as data
          processor within the meaning of the General Data Protection
          Regulation (GDPR). A data processing agreement is available on
          request.
        </LegalText>
        <LegalText>
          You may request deletion of data at any time, as described on our{" "}
          <Link href="/data-deletion" className={linkClass}>
            Data Deletion page
          </Link>
          .
        </LegalText>
      </LegalSection>

      <LegalSection title="10. Intellectual property">
        <LegalText>
          SmartTap, including its software, design and documentation, remains
          our property. Nothing in these Terms transfers ownership of it to
          you.
        </LegalText>
        <LegalText>
          Content you supply remains yours. You grant us a non-exclusive
          licence to use it only as necessary to provide the service to you.
        </LegalText>
      </LegalSection>

      <LegalSection title="11. Limitation of liability">
        <LegalText>
          Nothing in these Terms excludes or limits liability for death or
          personal injury caused by negligence, for fraud, or for any other
          liability which cannot lawfully be excluded.
        </LegalText>
        <LegalText>Subject to that:</LegalText>
        <LegalList
          items={[
            "We are not liable for indirect or consequential loss, including loss of profit, revenue, business or goodwill.",
            "We are not liable for loss arising from the acts, omissions, policy changes or unavailability of third-party platforms.",
            "Our total liability in any twelve-month period is limited to the total fees paid by you to us in that period.",
          ]}
        />
        <LegalText>
          The service is provided on a reasonable-efforts basis. We do not
          warrant that it will be uninterrupted or error-free.
        </LegalText>
      </LegalSection>

      <LegalSection title="12. Changes to these Terms">
        <LegalText>
          We may update these Terms from time to time. Where a change is
          material, we will give you reasonable notice before it takes effect.
          Continuing to use the service after that date constitutes
          acceptance.
        </LegalText>
      </LegalSection>

      <LegalSection title="13. Governing law">
        <LegalText>
          These Terms are governed by the laws of{" "}
          <strong className="text-electric-text">Ireland</strong>. The courts
          of Ireland have exclusive jurisdiction over any dispute arising from
          them.
        </LegalText>
        <LegalText>
          Nothing in this clause affects any statutory rights you may have as
          a consumer under Irish or EU law.
        </LegalText>
      </LegalSection>

      <LegalSection title="14. Contact">
        <LegalText>Questions about these Terms:</LegalText>
        <LegalText>
          <strong className="text-electric-text">Henrique Pasquetto</strong>,
          trading as Capivarex
          <br />
          Email:{" "}
          <a href="mailto:support@smarttap.ie" className={linkClass}>
            support@smarttap.ie
          </a>
          <br />
          Address: 46 Leinster Road, Rathmines, Dublin D06 R6K1, Ireland
        </LegalText>
      </LegalSection>
    </LegalPage>
  );
}

import type { Metadata } from "next";

import {
  LegalList,
  LegalPage,
  LegalSection,
  LegalText,
} from "../(legal)/_components/legal-page";

export const metadata: Metadata = {
  title: "Data Deletion Request",
  description:
    "How to request deletion of data held by SmartTap — no account or login needed. Email us and we handle it within 30 days, as required by the GDPR.",
};

const linkClass = "text-electric-cyan underline-offset-4 hover:underline";

export default function DataDeletionPage() {
  return (
    <LegalPage
      title="Data Deletion Request"
      intro="How to request deletion of data held by SmartTap, a service operated by Henrique Pasquetto, a sole trader established in Ireland, trading as Capivarex. You do not need an account or a login to make the request — email us and we will handle it."
      updated="29 July 2026"
    >
      <LegalSection title="How to request deletion">
        <LegalText>
          Send an email to{" "}
          <a href="mailto:support@smarttap.ie" className={linkClass}>
            support@smarttap.ie
          </a>{" "}
          with the subject line{" "}
          <strong className="text-electric-text">
            &quot;Data deletion request&quot;
          </strong>
          , including:
        </LegalText>
        <LegalList
          items={[
            "Your name",
            "The business you are connected to, if applicable (for example, the restaurant whose page or tag you used)",
            "The email address, phone number or account you would like removed",
          ]}
        />
        <LegalText>
          We will confirm receipt within{" "}
          <strong className="text-electric-text">7 days</strong> and complete
          the deletion within{" "}
          <strong className="text-electric-text">30 days</strong>, as required
          by the General Data Protection Regulation (GDPR).
        </LegalText>
        <LegalText>
          We may ask you to confirm your identity before proceeding. This is
          to make sure we are not deleting someone else&apos;s data at your
          request.
        </LegalText>
      </LegalSection>

      <LegalSection title="What data we may hold">
        <LegalText>
          Depending on how you have interacted with SmartTap, we may hold:
        </LegalText>
        <LegalText>
          <strong className="text-electric-text">
            If you are a customer of a business using SmartTap:
          </strong>
        </LegalText>
        <LegalList
          items={[
            "Loyalty programme records, such as visits, stamps collected and rewards issued",
            "Contact details you provided when joining a loyalty programme, such as name, email address or phone number",
            "Records of messages you sent to a business through a connected social media account, and the replies sent to you",
          ]}
        />
        <LegalText>
          <strong className="text-electric-text">
            If you are a business using SmartTap:
          </strong>
        </LegalText>
        <LegalList
          items={[
            "Your account details and business information, such as name, opening hours and menu content",
            "Reviews retrieved from your Google Business Profile and the replies generated or published",
            "Records of access you granted to third-party platforms, such as Google or Meta",
          ]}
        />
      </LegalSection>

      <LegalSection title="Deletion when an account is closed">
        <LegalText>
          If a business closes its SmartTap account, we retain its data for{" "}
          <strong className="text-electric-text">90 days</strong> to allow for
          reactivation and to settle any outstanding billing, after which it
          is deleted.
        </LegalText>
        <LegalText>
          Where we are required by law to retain certain records — for
          example, invoices and accounting records under Irish tax law — we
          retain only those records, for only as long as required.
        </LegalText>
      </LegalSection>

      <LegalSection title="Backups">
        <LegalText>
          Deleted data may persist in encrypted backups for a short period
          after deletion. These backups are overwritten on a rolling basis and
          are not used for any operational purpose.
        </LegalText>
      </LegalSection>

      <LegalSection title="Complaints">
        <LegalText>
          If you are not satisfied with how we handle your request, you may
          contact us at{" "}
          <a href="mailto:support@smarttap.ie" className={linkClass}>
            support@smarttap.ie
          </a>
          , or lodge a complaint with the Irish Data Protection Commission at{" "}
          <a
            href="https://www.dataprotection.ie"
            className={linkClass}
            rel="noopener noreferrer"
            target="_blank"
          >
            dataprotection.ie
          </a>
          .
        </LegalText>
      </LegalSection>

      <LegalSection title="Contact">
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

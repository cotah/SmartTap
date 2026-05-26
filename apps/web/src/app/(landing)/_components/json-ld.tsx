import * as React from "react";

/**
 * Structured data for the landing page — Organization + LocalBusiness +
 * SoftwareApplication. Helps Google understand SmartTap is (a) an Irish
 * company, (b) a SaaS, (c) operating out of Dublin.
 *
 * Rendered as a single <script type="application/ld+json"> block per the
 * Google Rich Results guidance. Marked with `dangerouslySetInnerHTML`
 * because the JSON must be inserted unescaped.
 *
 * If we later add an actual address, phone, or opening hours, extend the
 * LocalBusiness graph with those fields — Google rewards completeness.
 */
export function LandingJsonLd() {
  const SITE_URL =
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://smarttap.ie";

  const graph = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "@id": `${SITE_URL}#org`,
        name: "SmartTap",
        url: SITE_URL,
        logo: `${SITE_URL}/opengraph-image`,
        founder: {
          "@type": "Person",
          name: "Henrique Pasquetto",
          jobTitle: "Founder",
        },
        sameAs: [],
        contactPoint: [
          {
            "@type": "ContactPoint",
            email: "henrique@smarttap.ie",
            contactType: "customer support",
            areaServed: "IE",
            availableLanguage: ["en"],
          },
        ],
      },
      {
        "@type": "LocalBusiness",
        "@id": `${SITE_URL}#localbusiness`,
        name: "SmartTap",
        url: SITE_URL,
        image: `${SITE_URL}/opengraph-image`,
        description:
          "Loyalty and reviews stand for Dublin barbershops, cafés and small businesses. Tap to review and earn stamps — no app needed.",
        address: {
          "@type": "PostalAddress",
          addressLocality: "Dublin",
          addressCountry: "IE",
        },
        areaServed: [
          {
            "@type": "City",
            name: "Dublin",
          },
        ],
      },
      {
        "@type": "SoftwareApplication",
        "@id": `${SITE_URL}#app`,
        name: "SmartTap",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: {
          "@type": "AggregateOffer",
          priceCurrency: "EUR",
          lowPrice: "29",
          highPrice: "179",
          offerCount: 4,
        },
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      // The JSON-LD spec demands unescaped JSON, which is also why React
      // requires `dangerouslySetInnerHTML` here. Content is fully built
      // from constants — no untrusted input.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(graph) }}
    />
  );
}

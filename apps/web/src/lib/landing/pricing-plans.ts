/**
 * Pricing data for the landing grid. Source of truth for plan copy +
 * numbers — change here, the grid updates everywhere.
 *
 * Keep in sync with backend STRIPE_PRICE_* env vars and the founding
 * member offer (which is a SEPARATE callout, not in this grid).
 */

export interface Plan {
  id: "review" | "loyalty" | "pro" | "network";
  name: string;
  tagline: string;
  setupFeeEur: number;
  monthlyEur: number;
  customerCap: string;
  features: string[];
  /** True for the "Most popular" plan — drives the highlight treatment. */
  highlight?: boolean;
}

export const PLANS: Plan[] = [
  {
    id: "review",
    name: "SmartReview",
    tagline: "For shops focused on reviews",
    setupFeeEur: 49,
    monthlyEur: 29,
    customerCap: "Up to 200 customers",
    features: [
      "One NFC stand included",
      "Google Reviews tracking",
      "Email support",
    ],
  },
  {
    id: "loyalty",
    name: "SmartLoyalty",
    tagline: "Reviews plus digital stamps",
    setupFeeEur: 79,
    monthlyEur: 59,
    customerCap: "Up to 500 customers",
    features: [
      "Two NFC stands included",
      "Stamps and rewards system",
      "Customer database — yours to keep",
    ],
    highlight: true,
  },
  {
    id: "pro",
    name: "SmartPro",
    tagline: "For shops that want everything",
    setupFeeEur: 149,
    monthlyEur: 99,
    customerCap: "Unlimited customers",
    features: [
      "Three NFC stands included",
      "Campaigns, WhatsApp, monthly reports",
      "Priority support from the founder",
    ],
  },
  {
    id: "network",
    name: "SmartNetwork",
    tagline: "For multi-location owners",
    setupFeeEur: 299,
    monthlyEur: 179,
    customerCap: "Unlimited customers, unlimited shops",
    features: [
      "Five NFC stands included",
      "One dashboard for every location",
      "Dedicated account manager",
    ],
  },
];

export const PRICING_CTA_LABEL = "Start free trial";

import * as React from "react";

import { PLANS } from "@/lib/landing/pricing-plans";

import { Section, SectionEyebrow } from "../section";

import { FoundingCallout } from "./founding-callout";
import { PricingCard } from "./pricing-card";

/**
 * Section 4 — Pricing.
 *
 * Four-plan grid + founding callout + cancel-anytime trust line. Grid
 * collapses gracefully: 4 columns on desktop, 2 columns on tablet, 1
 * column on mobile. Most-popular card lifts slightly via scale on
 * desktop only — preserves alignment on the 2-up tablet view.
 *
 * Plan data lives in `lib/landing/pricing-plans.ts`. Update there to
 * change copy or numbers without touching this file.
 */
export function Pricing() {
  return (
    <Section id="pricing">
      <header className="mb-10 flex flex-col items-start gap-4 md:mb-14">
        <SectionEyebrow>Pricing</SectionEyebrow>
        <h2 className="max-w-[820px] font-display text-3xl leading-tight tracking-[-0.02em] text-neutral-900 md:text-[44px]">
          Simple pricing. No contracts.
        </h2>
        <p className="max-w-[640px] text-base leading-relaxed text-neutral-600 md:text-lg">
          Setup fee covers your custom 3D-printed stand, shipped from Dublin.
          Monthly covers the software, the data hosting, the WhatsApp send,
          and the founder on email when something breaks.
        </p>
      </header>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5">
        {PLANS.map((plan) => (
          <PricingCard key={plan.id} plan={plan} />
        ))}
      </div>

      <FoundingCallout />

      <p className="mt-8 text-sm text-neutral-600 md:text-[15px]">
        30-day free trial. No card to start. Cancel any time — your data
        exports with you.
      </p>
    </Section>
  );
}

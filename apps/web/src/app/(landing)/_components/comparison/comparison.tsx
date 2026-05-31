import * as React from "react";

import { Section, SectionEyebrow } from "../section";

import { ComparisonAccordion } from "./comparison-accordion";
import { ComparisonTable } from "./comparison-table";

/**
 * Section 6 — Comparison.
 *
 * Post-pricing per CEO reorder (LANDING-SPEC.md C4). Renders a table on
 * desktop (the 5-axis grid fits comfortably), an accordion on mobile
 * (avoids horizontal scroll). Both consume the same data from
 * `comparison-data.ts`.
 */
export function Comparison() {
  return (
    <Section id="comparison">
      <header className="mb-10 flex flex-col items-start gap-4 md:mb-12">
        <SectionEyebrow>Why shops switch</SectionEyebrow>
        <h2 className="max-w-[820px] font-display text-3xl font-semibold leading-tight tracking-[-0.02em] text-electric-text md:text-[44px]">
          Why shops switch to SmartTap.
        </h2>
        <p className="max-w-[640px] text-base leading-relaxed text-electric-text-muted md:text-lg">
          Five things owners ask about before signing. Five honest answers.
        </p>
      </header>

      <ComparisonTable />
      <ComparisonAccordion />
    </Section>
  );
}

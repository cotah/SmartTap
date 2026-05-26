import { Nfc, RotateCcw, Star } from "lucide-react";
import * as React from "react";

import { Section, SectionEyebrow } from "../section";

import { StepCard } from "./step-card";

/**
 * Section 3 — How It Works.
 *
 * Three step cards in a 3-column grid on desktop, stacked on mobile. The
 * 5-minute setup promise sits below the grid as a quiet trust line — not
 * styled as a CTA. Numbers (01/02/03) carry the structural feel; lucide
 * icons (Nfc / Star / RotateCcw) carry the metaphor.
 */
const STEPS = [
  {
    number: "01",
    title: "They tap the stand",
    body:
      "Phone touches the stand. Page opens. No app, no download, nothing to install.",
    icon: <Nfc className="h-7 w-7 stroke-[1.5]" />,
  },
  {
    number: "02",
    title: "They leave a review",
    body:
      "One tap sends them straight to your Google page. Stamp gets added too.",
    icon: <Star className="h-7 w-7 stroke-[1.5]" />,
  },
  {
    number: "03",
    title: "They come back",
    body:
      "Stamps fill up. Reward unlocks. You message them direct — no middleman.",
    icon: <RotateCcw className="h-7 w-7 stroke-[1.5]" />,
  },
];

export function HowItWorks() {
  return (
    <Section id="how-it-works">
      <header className="mb-12 flex flex-col items-start gap-4 md:mb-16">
        <SectionEyebrow>How it works</SectionEyebrow>
        <h2 className="max-w-[680px] font-display text-3xl leading-tight tracking-[-0.02em] text-neutral-900 md:text-[44px]">
          They tap. They review. They come back.
        </h2>
      </header>

      <ol className="grid gap-6 md:grid-cols-3 md:gap-8">
        {STEPS.map((step, i) => (
          <li key={step.number} className="h-full">
            <StepCard {...step} delay={i * 0.08} />
          </li>
        ))}
      </ol>

      <p className="mt-12 text-sm text-neutral-600 md:mt-16 md:text-[15px]">
        Five-minute setup. We ship the stand, you stick the reward, your
        customers do the rest.
      </p>
    </Section>
  );
}

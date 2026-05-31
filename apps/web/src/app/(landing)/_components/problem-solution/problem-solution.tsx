import * as React from "react";

import { Section, SectionEyebrow } from "../section";

import { ProblemCard } from "./problem-card";

/**
 * Section 5 — Problem → Solution.
 *
 * Comes AFTER pricing per CEO reorder (LANDING-SPEC.md C2). The skeptical
 * reader has now seen the price and the demo; this section confirms the
 * pain they came in with, then names SmartTap as the close.
 *
 * The transition line "SmartTap turns one tap into both." is the heart
 * of the section — bigger and amber-accented. Not a CTA, just a sentence
 * that earns the right to send the reader back up to pricing.
 */
const PROBLEMS = [
  {
    number: "Problem 01",
    text: "You ask for reviews. Most never leave one.",
  },
  {
    number: "Problem 02",
    text: "Regulars stop coming. You never find out why.",
  },
  {
    number: "Problem 03",
    text: "You pay for ads to bring strangers in.",
  },
];

export function ProblemSolution() {
  return (
    <Section id="problem" className="bg-electric-surface/30">
      <header className="mb-12 flex flex-col items-start gap-4 md:mb-16">
        <SectionEyebrow>The honest part</SectionEyebrow>
        <h2 className="font-display text-3xl font-semibold leading-tight tracking-[-0.02em] text-electric-text md:text-[44px]">
          Sound familiar?
        </h2>
      </header>

      <ul className="grid gap-10 md:grid-cols-3 md:gap-8">
        {PROBLEMS.map((p, i) => (
          <li key={p.number}>
            <ProblemCard {...p} delay={i * 0.08} />
          </li>
        ))}
      </ul>

      <div className="mt-16 max-w-[820px] md:mt-20">
        <p className="font-display text-2xl font-semibold leading-tight tracking-[-0.01em] text-electric-text md:text-3xl lg:text-[34px]">
          SmartTap turns one tap into{" "}
          <span className="relative inline-block text-electric-cyan">
            both
            <svg
              aria-hidden="true"
              className="absolute -bottom-1 left-0 h-2 w-full md:-bottom-1.5 md:h-3"
              viewBox="0 0 80 12"
              preserveAspectRatio="none"
              style={{ filter: "drop-shadow(0 0 6px rgba(0,212,255,0.7))" }}
            >
              <path
                d="M2 8 Q20 2 40 6 T78 8"
                stroke="#00D4FF"
                strokeWidth="3"
                strokeLinecap="round"
                fill="none"
              />
            </svg>
          </span>
          .
        </p>
        <p className="mt-4 max-w-[640px] text-base leading-relaxed text-electric-text-muted md:text-lg">
          A review that pulls a stranger in. A stamp that brings the regular
          back. One tap on the counter, both jobs done.
        </p>
      </div>
    </Section>
  );
}

import * as React from "react";

import { AnimatedDemo } from "./_components/animated-demo/animated-demo";
import { Comparison } from "./_components/comparison/comparison";
import { Hero } from "./_components/hero/hero";
import { HowItWorks } from "./_components/how-it-works/how-it-works";
import { Pricing } from "./_components/pricing/pricing";
import { ProblemSolution } from "./_components/problem-solution/problem-solution";
import { Section, SectionEyebrow } from "./_components/section";

/**
 * SmartTap landing — composes the 8 marketing sections per LANDING-SPEC.md.
 *
 * Order is locked (CEO reorder accepted 2026-05-26):
 *   Hero → Demo → How → Pricing → Problem → Comparison → FAQ → CTA Final
 *
 * Each section is a sibling here. The (landing) layout wraps everything in
 * `<main id="main">` with the TopBanner + Footer chrome. Cream page
 * background + neutral-900 text are inherited from the layout, so each
 * section only opts into colour where the visual rhythm demands it
 * (Pricing highlighted card, Footer dark, etc).
 */
export default function LandingPage() {
  return (
    <>
      {/* 1. Hero */}
      <Hero />

      {/* 2. Animated demo */}
      <AnimatedDemo />

      {/* 3. How it works */}
      <HowItWorks />

      {/* 4. Pricing */}
      <Pricing />

      {/* 5. Problem → Solution */}
      <ProblemSolution />

      {/* 6. Comparison */}
      <Comparison />

      {/* 7. FAQ — Phase 5 */}
      <Section as="section" id="faq" containerSize="narrow">
        <Placeholder
          eyebrow="Section 7 · FAQ"
          title="Common questions"
          subtitle="Eight Q/A accordion built on Radix."
        />
      </Section>

      {/* 8. CTA Final — Phase 5 */}
      <Section as="section" id="cta-final" containerSize="hero">
        <Placeholder
          eyebrow="Section 8 · Founding offer"
          title="Five shops. One price. Locked for life."
          subtitle="Offer block with primary + alt CTAs."
        />
      </Section>
    </>
  );
}

/**
 * Phase-1-only placeholder. Renders the section structure end-to-end so
 * design rhythm (py-32, type scale, container widths) is verifiable on
 * the live page from day one. Replaced in subsequent phases.
 */
function Placeholder({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex flex-col items-start gap-4 rounded-2xl border border-dashed border-neutral-300 bg-cream/60 p-8 md:p-12">
      <SectionEyebrow>{eyebrow}</SectionEyebrow>
      <h2 className="font-display text-3xl leading-tight md:text-4xl">{title}</h2>
      <p className="max-w-[680px] text-base leading-relaxed text-neutral-600 md:text-lg">
        {subtitle}
      </p>
    </div>
  );
}

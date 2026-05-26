import * as React from "react";

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
      {/* 1. Hero — Phase 2 */}
      <Section as="section" id="hero" containerSize="hero" className="lg:pt-24 lg:pb-32">
        <Placeholder
          eyebrow="Section 1 · Hero"
          title="One tap. Reviews go up. Regulars come back."
          subtitle="Hero block lands in Phase 2 — H1, subhead, two CTAs, photo of the real stand, founder microtrust line."
        />
      </Section>

      {/* 2. Animated demo — Phase 2 */}
      <Section as="section" id="demo">
        <Placeholder
          eyebrow="Section 2 · Demo"
          title="This is what your customers see."
          subtitle="Animated SVG: stand pulse → phone slide → tap ripple → review submitted. 4.5s loop, pauses off-screen, simplified on mobile, static for reduced-motion."
        />
      </Section>

      {/* 3. How it works — Phase 3 */}
      <Section as="section" id="how-it-works">
        <Placeholder
          eyebrow="Section 3 · How it works"
          title="They tap. They review. They come back."
          subtitle="Three step cards with icons + 5-minute setup promise."
        />
      </Section>

      {/* 4. Pricing — Phase 4 */}
      <Section as="section" id="pricing">
        <Placeholder
          eyebrow="Section 4 · Pricing"
          title="Simple pricing. No contracts."
          subtitle="Four-plan grid with SmartLoyalty highlighted. Founding-member callout under grid."
        />
      </Section>

      {/* 5. Problem → Solution — Phase 3 */}
      <Section as="section" id="problem">
        <Placeholder
          eyebrow="Section 5 · Problem"
          title="Sound familiar?"
          subtitle="Three punch-list problems in owner's voice → transition into the SmartTap close."
        />
      </Section>

      {/* 6. Comparison — Phase 4 */}
      <Section as="section" id="comparison">
        <Placeholder
          eyebrow="Section 6 · Comparison"
          title="Why shops switch to SmartTap"
          subtitle="Five-axis table vs typical alternatives. Mobile renders as accordion."
        />
      </Section>

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

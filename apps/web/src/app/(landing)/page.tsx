import * as React from "react";

import { AnimatedDemo } from "./_components/animated-demo/animated-demo";
import { Comparison } from "./_components/comparison/comparison";
import { CtaFinal } from "./_components/cta-final";
import { Faq } from "./_components/faq/faq";
import { Hero } from "./_components/hero/hero";
import { HowItWorks } from "./_components/how-it-works/how-it-works";
import { Pricing } from "./_components/pricing/pricing";
import { ProblemSolution } from "./_components/problem-solution/problem-solution";

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

      {/* 7. FAQ */}
      <Faq />

      {/* 8. CTA Final */}
      <CtaFinal />
    </>
  );
}

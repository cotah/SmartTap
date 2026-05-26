import * as React from "react";

import { Section } from "../section";

import { HeroContent } from "./hero-content";
import { HeroMockup } from "./hero-mockup";

/**
 * Hero — Section 1 of the landing.
 *
 * Server-rendered shell; only `HeroMockup` is client (for the parallax /
 * NFC wave animation). Two-column on desktop (text 58% / visual 42%),
 * stacks on mobile.
 *
 * Top padding is reduced from the standard `py-32` (`pt-12 lg:pt-20`)
 * because the sticky `TopBanner` already adds visual height above. CTA
 * Final brings back the full `py-32` rhythm at the bottom of the page.
 */
export function Hero() {
  return (
    <Section
      id="hero"
      containerSize="hero"
      className="pt-12 sm:pt-16 lg:pt-20 lg:pb-32"
    >
      <div className="grid items-center gap-12 lg:grid-cols-[1.2fr_1fr] lg:gap-16">
        <HeroContent />
        <HeroMockup />
      </div>
    </Section>
  );
}

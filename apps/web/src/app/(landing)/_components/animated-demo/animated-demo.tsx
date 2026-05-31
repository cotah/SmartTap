"use client";

import { useInView } from "framer-motion";
import * as React from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";

import { SectionEyebrow } from "../section";

import {
  DemoDefs,
  MotionPhone,
  MotionRipple,
  MotionStand,
} from "./demo-svg";

/**
 * Section 2 — animated SVG demo of the tap-to-review loop.
 *
 * Loops indefinitely while in viewport (paused otherwise) per LANDING-SPEC
 * §5. Reduced-motion users see the end-state — phone showing the review
 * submitted confirmation, no motion at all.
 *
 * The whole timeline is 4.5s + 0.8s pause = 5.3s per cycle. Children in
 * `demo-svg.tsx` each consume the same `playing` flag and run their own
 * keyframes pinned to normalized [0..1] timepoints. That keeps the SVG
 * tree as a regular React render — no requestAnimationFrame loop, no
 * orchestrator state churn.
 */
export function AnimatedDemo() {
  const sectionRef = React.useRef<HTMLElement>(null);
  // `useInView` from framer-motion is SSR-safe + reactive. We pause the
  // animations when the section scrolls off-screen so we don't burn CPU.
  const inView = useInView(sectionRef, { amount: 0.3 });
  const reduced = useReducedMotion();
  const playing = inView && !reduced;

  return (
    <section
      ref={sectionRef}
      id="demo"
      className="px-6 py-18 sm:py-24 md:px-12 lg:px-16 lg:py-32"
    >
      <div className="mx-auto max-w-[1200px]">
        <div className="grid items-center gap-12 lg:grid-cols-[1fr_1.1fr] lg:gap-20">
          {/* Left: caption */}
          <div className="flex flex-col gap-5">
            <SectionEyebrow>The interaction</SectionEyebrow>
            <h2 className="font-display text-3xl font-semibold leading-[1.1] tracking-[-0.02em] md:text-4xl lg:text-[44px]">
              This is what your customers see.
              <br />
              <span className="text-electric-cyan">One tap. That&apos;s it.</span>
            </h2>
            <p className="max-w-[480px] text-base leading-relaxed text-electric-text-muted md:text-lg">
              No app to download. No QR code to scan. No menu to navigate. The
              phone touches the stand, the page opens, and the review takes
              one tap to send.
            </p>
            <ul className="mt-2 grid gap-3 text-sm text-electric-text-muted md:text-[15px]">
              <li className="flex items-start gap-2">
                <Bullet />
                <span>
                  Works on every modern iPhone and Android — no extra hardware
                  for your customer.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Bullet />
                <span>
                  Uses the customer&apos;s own data. Your shop Wi-Fi doesn&apos;t
                  even need to be on.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Bullet />
                <span>
                  Loyalty stamp gets added in the background. Your dashboard
                  fills up while they finish their coffee.
                </span>
              </li>
            </ul>
          </div>

          {/* Right: animated demo canvas */}
          <div className="relative">
            <div
              aria-hidden="true"
              className="absolute inset-x-0 inset-y-8 -z-10 rounded-[40%] bg-electric-cyan/15 blur-3xl"
            />
            <svg
              viewBox="0 0 500 400"
              className="h-auto w-full"
              role="img"
              aria-label="Animation showing a customer tapping a SmartTap stand with their phone, which opens a review screen and submits a 5-star rating."
            >
              <title>One-tap review demo</title>
              <DemoDefs />
              <MotionStand playing={playing} />
              <MotionPhone playing={playing} />
              <MotionRipple playing={playing} />
            </svg>
          </div>
        </div>
      </div>
    </section>
  );
}

function Bullet() {
  return (
    <span
      aria-hidden="true"
      className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-electric-cyan"
    />
  );
}

"use client";

import { motion, type Variants } from "framer-motion";
import * as React from "react";

import { useScrollFadeIn } from "@/lib/hooks/use-scroll-fade-in";
import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

/**
 * Drop-in wrapper for scroll-triggered fade-in.
 *
 * Pairs `useScrollFadeIn` with framer-motion. Reduced-motion users render
 * straight to the final state — no animation, no `style` thrash. The
 * 600ms duration + `smooth-out` easing (cubic-bezier(0.16, 1, 0.3, 1))
 * match the LANDING-SPEC §4 rhythm.
 *
 * For staggered children (e.g. 3 problem cards, 3 how-it-works steps),
 * wrap each in a ScrollFade with an incrementing `delay` of 80ms.
 */
type ScrollFadeProps = {
  delay?: number;
  className?: string;
  /** Element type to render. Default `div`. Use `li` inside lists. */
  as?: "div" | "li" | "span" | "section";
  children: React.ReactNode;
};

const variants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
};

export function ScrollFade({
  delay = 0,
  className,
  as = "div",
  children,
}: ScrollFadeProps) {
  const [ref, visible] = useScrollFadeIn<HTMLDivElement>();
  const reduced = useReducedMotion();

  // Per Variants TS, motion.* keys are typed strictly. Cast for the
  // dynamic element — the only allowed `as` values are listed in props.
  const MotionTag = motion[as] as typeof motion.div;

  return (
    <MotionTag
      ref={ref}
      initial={reduced ? "visible" : "hidden"}
      animate={visible ? "visible" : "hidden"}
      variants={variants}
      transition={{
        duration: 0.6,
        delay: reduced ? 0 : delay,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={cn(className)}
    >
      {children}
    </MotionTag>
  );
}

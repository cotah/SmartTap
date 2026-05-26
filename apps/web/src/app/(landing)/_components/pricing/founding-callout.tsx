"use client";

import { ArrowRight } from "lucide-react";
import * as React from "react";

import { useCounter } from "@/lib/hooks/use-counter";
import { useScrollFadeIn } from "@/lib/hooks/use-scroll-fade-in";
import {
  FOUNDING_SPOTS_REMAINING,
  FOUNDING_TOTAL,
} from "@/lib/landing/constants";
import { cn } from "@/lib/utils";

import { LandingButton } from "../button";

/**
 * Founding-member callout under the pricing grid.
 *
 * The counter ticks 0 → FOUNDING_SPOTS_REMAINING when the section scrolls
 * into view. Reduced-motion users see the final value immediately.
 *
 * When `FOUNDING_SPOTS_REMAINING` is 0 we hide the whole callout — the
 * top banner has already announced "offer closed" and we don't want to
 * dangle a dead CTA under the pricing grid.
 */
export function FoundingCallout() {
  const [ref, visible] = useScrollFadeIn<HTMLDivElement>();
  const [value] = useCounter(FOUNDING_SPOTS_REMAINING, {
    duration: 1800,
    autoStart: visible,
  });

  if (FOUNDING_SPOTS_REMAINING <= 0) return null;

  return (
    <div
      ref={ref}
      className={cn(
        "mt-10 flex flex-col gap-4 rounded-2xl border border-amber-500/60 bg-amber-50/70 p-6 md:mt-12 md:flex-row md:items-center md:justify-between md:gap-8 md:p-8",
        "transition-opacity duration-700",
        visible ? "opacity-100" : "opacity-0",
      )}
    >
      <div className="flex flex-col gap-2">
        <p className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-amber-600">
          Founding members only
        </p>
        <p className="font-display text-2xl leading-tight tracking-tight text-neutral-900 md:text-[26px]">
          First{" "}
          <span className="text-amber-600">
            {/* Visual animating count — hidden from screen readers so the
             * tween doesn't trigger N announcements as it climbs. */}
            <span aria-hidden="true">
              {visible ? value : 0} of {FOUNDING_TOTAL}
            </span>
            {/* sr-only static value — single announcement on entry. */}
            <span className="sr-only">
              {FOUNDING_SPOTS_REMAINING} of {FOUNDING_TOTAL}
            </span>
          </span>{" "}
          Dublin shops:&nbsp;stand&nbsp;free,&nbsp;60&nbsp;days&nbsp;free, €29/mo locked for life.
        </p>
      </div>
      <LandingButton href="#cta-final" variant="primary" size="lg" className="shrink-0">
        Claim my founding spot
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </LandingButton>
    </div>
  );
}

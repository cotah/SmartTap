import { Star } from "lucide-react";
import * as React from "react";

import { FOUNDER_MICROTRUST } from "@/lib/landing/constants";

import { BookCallButton } from "../book-call-button";
import { LandingButton } from "../button";
import { TextRepel } from "../effects/text-repel";

/**
 * Hero text block — eyebrow + H1 + subhead + two CTAs + microtrust line.
 *
 * H1 is the LANDING-SPEC.md locked copy: "One tap. Reviews go up. Regulars
 * come back." Set in Geist Sans at 64px desktop / 40px mobile. Each line is
 * a Text Repel field — letters drift from the cursor (subtle-drift variant),
 * the single premium interaction the headline allows itself. The cyan-
 * underlined `Reviews` is the accent moment.
 *
 * CTAs are stacked on mobile (full-width), inline on `sm:` and up. The
 * "Start free" path goes to /signup directly; the founder call opens a
 * Cal.com dialog (or mailto if env not configured yet).
 */
export function HeroContent() {
  return (
    <div className="flex flex-col items-start gap-6 md:gap-7">
      <p className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-electric-cyan">
        Built in Dublin, for Dublin shops.
      </p>

      <h1 className="font-display text-[40px] font-semibold leading-[1.06] tracking-[-0.02em] text-electric-text md:text-[56px] lg:text-[64px]">
        <TextRepel>One tap.</TextRepel>
        <br />
        <span className="relative inline-block">
          <TextRepel>Reviews</TextRepel>
          {/* Cyan underline accent + soft glow — the headline's one neon
           * moment in the Dark Electric palette. */}
          <svg
            aria-hidden="true"
            className="absolute -bottom-1 left-0 h-2 w-full md:-bottom-2 md:h-3"
            viewBox="0 0 200 12"
            preserveAspectRatio="none"
            style={{ filter: "drop-shadow(0 0 6px rgba(0,212,255,0.7))" }}
          >
            <path
              d="M2 8 Q40 2 100 6 T198 8"
              stroke="#00D4FF"
              strokeWidth="3"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        </span>{" "}
        <TextRepel>go up.</TextRepel>
        <br />
        <TextRepel>Regulars come back.</TextRepel>
      </h1>

      <p className="max-w-[560px] text-lg leading-relaxed text-electric-text-muted md:text-xl">
        Your stand. Your customers. Your data. Not stuck inside someone else&apos;s app.
      </p>

      <div className="mt-2 flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center">
        <LandingButton href="/signup" variant="primary" size="lg" className="w-full sm:w-auto">
          Start free — no card needed
        </LandingButton>
        <BookCallButton variant="secondary" size="lg" className="w-full sm:w-auto" />
      </div>

      {/* Microtrust — the founder-replaces-logos line per CEO advisor.
       * Stars in cyan; separator dots in the near-invisible border tone. */}
      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm leading-relaxed text-electric-text-muted">
        <span aria-label="5 out of 5" className="flex items-center gap-0.5 text-electric-cyan">
          {Array.from({ length: 5 }).map((_, i) => (
            <Star key={i} className="h-4 w-4 fill-current" aria-hidden="true" />
          ))}
        </span>
        <span>{FOUNDER_MICROTRUST}</span>
        <span aria-hidden="true" className="text-electric-border">·</span>
        <span>GDPR-ready</span>
        <span aria-hidden="true" className="text-electric-border">·</span>
        <span>No app for your customers</span>
      </p>
    </div>
  );
}

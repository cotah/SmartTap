import { ArrowRight, Check } from "lucide-react";
import * as React from "react";

import {
  FOUNDING_SPOTS_REMAINING,
  FOUNDING_TOTAL,
} from "@/lib/landing/constants";

import { LandingButton } from "./button";
import { Section, SectionEyebrow } from "./section";

/**
 * Section 8 — Final CTA. The founding-member close.
 *
 * Dark green background full-bleed at the bottom of the page. The amber
 * count is the only amber on this section — drives the eye to "5 spots
 * total" before it lands on the CTA button.
 *
 * When `FOUNDING_SPOTS_REMAINING` is 0 the offer is closed; we still
 * render the section but swap the heading + body to the standard-pricing
 * narrative and remove the founding-spot line. The "Start a 30-day
 * trial" alt link becomes the primary CTA.
 */
export function CtaFinal() {
  const offerOpen = FOUNDING_SPOTS_REMAINING > 0;

  return (
    <Section
      id="cta-final"
      containerSize="hero"
      className="bg-green-900 text-cream"
    >
      <div className="grid items-start gap-12 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
        {/* Left: pitch */}
        <div className="flex flex-col gap-6">
          <SectionEyebrow className="text-amber-500">
            <span className="bg-amber-500 inline-block h-1.5 w-1.5 rounded-full" />
            {offerOpen ? "Founding offer" : "Standard pricing"}
          </SectionEyebrow>
          <h2 className="font-display text-4xl leading-[1.05] tracking-[-0.02em] md:text-5xl lg:text-[56px]">
            {offerOpen ? (
              <>
                Five shops. One price.
                <br />
                <span className="text-amber-500">Locked for life.</span>
              </>
            ) : (
              <>
                Try SmartTap free for 30 days.
                <br />
                <span className="text-amber-500">No card to start.</span>
              </>
            )}
          </h2>
          <p className="max-w-[560px] text-base leading-relaxed text-cream/80 md:text-lg">
            {offerOpen
              ? "Founding members get the stand free and €29/month forever — long after public pricing goes up. We pick five shops we want to ship with first. After that, the offer closes."
              : "Setup arrives in the post within five working days. If it doesn't work for your shop, export every customer record and cancel in two clicks. No notice, no questions."}
          </p>
        </div>

        {/* Right: offer block + CTAs */}
        <div className="rounded-2xl border border-amber-500/40 bg-green-900/30 p-6 backdrop-blur-sm md:p-8">
          {offerOpen ? (
            <>
              <dl className="flex flex-col gap-5">
                <OfferLine
                  label="You get"
                  body="Free custom stand, 60 days free, €29/mo locked for life."
                />
                <OfferLine
                  label="You give"
                  body="A short video saying what worked, and two shops we should talk to."
                />
                <OfferLine
                  label="Closing"
                  body={`${FOUNDING_SPOTS_REMAINING} of ${FOUNDING_TOTAL} spots still open. First come, first served.`}
                />
              </dl>
              <div className="mt-7 flex flex-col gap-3">
                <LandingButton
                  href="/signup?plan=founding"
                  variant="primary"
                  size="lg"
                  className="w-full border border-amber-500 bg-amber-500 text-neutral-900 hover:border-amber-600 hover:bg-amber-600 hover:text-neutral-900"
                >
                  Claim my founding spot
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </LandingButton>
                <a
                  href="/signup"
                  className="text-center text-sm text-cream/70 underline-offset-4 transition-colors hover:text-amber-500 hover:underline"
                >
                  Not a founder? Start a free 30-day trial instead →
                </a>
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-6">
              <p className="text-base leading-relaxed text-cream/85">
                Pick the plan that fits. No contracts, full data export,
                cancel any time.
              </p>
              <LandingButton
                href="/signup"
                variant="primary"
                size="lg"
                className="w-full border border-amber-500 bg-amber-500 text-neutral-900 hover:border-amber-600 hover:bg-amber-600 hover:text-neutral-900"
              >
                Start free 30-day trial
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </LandingButton>
            </div>
          )}
        </div>
      </div>
    </Section>
  );
}

function OfferLine({ label, body }: { label: string; body: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-amber-500">
        <Check className="h-3 w-3" strokeWidth={3} aria-hidden="true" />
      </span>
      <div className="flex flex-col gap-0.5">
        <dt className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-amber-500">
          {label}
        </dt>
        <dd className="text-[15px] leading-relaxed text-cream/90 md:text-base">
          {body}
        </dd>
      </div>
    </div>
  );
}

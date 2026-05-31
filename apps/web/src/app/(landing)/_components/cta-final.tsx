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
      className="border-t border-electric-border bg-electric-bg text-electric-text [background-image:radial-gradient(ellipse_80%_60%_at_50%_0%,rgba(0,212,255,0.14),transparent)]"
    >
      <div className="grid items-start gap-12 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
        {/* Left: pitch */}
        <div className="flex flex-col gap-6">
          <SectionEyebrow>
            {offerOpen ? "Founding offer" : "Standard pricing"}
          </SectionEyebrow>
          <h2 className="font-display text-4xl font-semibold leading-[1.05] tracking-[-0.02em] md:text-5xl lg:text-[56px]">
            {offerOpen ? (
              <>
                Five shops. One price.
                <br />
                <span className="text-electric-cyan">Locked for life.</span>
              </>
            ) : (
              <>
                Try SmartTap free for 30 days.
                <br />
                <span className="text-electric-cyan">No card to start.</span>
              </>
            )}
          </h2>
          <p className="max-w-[560px] text-base leading-relaxed text-electric-text-muted md:text-lg">
            {offerOpen
              ? "Founding members get the stand free and €29/month forever — long after public pricing goes up. We pick five shops we want to ship with first. After that, the offer closes."
              : "Setup arrives in the post within five working days. If it doesn't work for your shop, export every customer record and cancel in two clicks. No notice, no questions."}
          </p>
        </div>

        {/* Right: offer block + CTAs */}
        <div className="rounded-2xl border border-electric-cyan/40 bg-electric-surface/60 p-6 shadow-[0_0_40px_rgba(0,212,255,0.12)] backdrop-blur-sm md:p-8">
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
                  className="w-full"
                >
                  Claim my founding spot
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </LandingButton>
                <a
                  href="/signup"
                  className="text-center text-sm text-electric-text-muted underline-offset-4 transition-colors hover:text-electric-cyan hover:underline"
                >
                  Not a founder? Start a free 30-day trial instead →
                </a>
              </div>
            </>
          ) : (
            <div className="flex flex-col gap-6">
              <p className="text-base leading-relaxed text-electric-text-muted">
                Pick the plan that fits. No contracts, full data export,
                cancel any time.
              </p>
              <LandingButton
                href="/signup"
                variant="primary"
                size="lg"
                className="w-full"
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
      <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-electric-cyan/15 text-electric-cyan">
        <Check className="h-3 w-3" strokeWidth={3} aria-hidden="true" />
      </span>
      <div className="flex flex-col gap-0.5">
        <dt className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-electric-cyan">
          {label}
        </dt>
        <dd className="text-[15px] leading-relaxed text-electric-text-muted md:text-base">
          {body}
        </dd>
      </div>
    </div>
  );
}

import { Check } from "lucide-react";
import * as React from "react";

import type { Plan } from "@/lib/landing/pricing-plans";
import { PRICING_CTA_LABEL } from "@/lib/landing/pricing-plans";
import { cn } from "@/lib/utils";

import { LandingButton } from "../button";

/**
 * Single pricing card.
 *
 * Two visual variants driven by `plan.highlight`:
 * - Default: cream background, neutral border, green CTA
 * - Highlighted ("Most popular"): green-900 background, cream text, amber
 *   badge, slightly lifted via shadow and a 1px amber ring
 *
 * Setup fee is the visual hook (€49+) but monthly is the larger number —
 * the eye is supposed to land on €29/mo first. Per-plan features stay
 * short (3 lines max) so all four cards fit one screen on a 13" laptop.
 */
export function PricingCard({ plan }: { plan: Plan }) {
  const highlighted = !!plan.highlight;

  return (
    <article
      className={cn(
        "relative flex h-full flex-col rounded-2xl border p-6 transition-colors md:p-7",
        highlighted
          ? "border-amber-500 bg-green-900 text-cream shadow-xl ring-1 ring-amber-500/40 md:scale-[1.02]"
          : "border-neutral-300 bg-cream text-neutral-900 shadow-sm hover:border-green-900/30",
      )}
    >
      {highlighted && (
        <span
          className={cn(
            "absolute -top-3 left-1/2 -translate-x-1/2 rounded-full",
            "bg-amber-500 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.1em] text-neutral-900",
          )}
        >
          ★ Most popular
        </span>
      )}

      <header className="flex flex-col gap-1">
        <h3
          className={cn(
            "font-display text-2xl leading-tight tracking-tight",
            highlighted ? "text-cream" : "text-neutral-900",
          )}
        >
          {plan.name}
        </h3>
        <p
          className={cn(
            "text-sm",
            highlighted ? "text-cream/75" : "text-neutral-600",
          )}
        >
          {plan.tagline}
        </p>
      </header>

      <div className="mt-6 flex flex-col gap-1">
        <p className="flex items-baseline gap-1">
          <span
            className={cn(
              "font-display text-[40px] leading-none tracking-tight",
              highlighted ? "text-cream" : "text-neutral-900",
            )}
          >
            €{plan.monthlyEur}
          </span>
          <span
            className={cn(
              "text-sm",
              highlighted ? "text-cream/75" : "text-neutral-600",
            )}
          >
            /month
          </span>
        </p>
        <p
          className={cn(
            "text-[13px]",
            highlighted ? "text-cream/70" : "text-neutral-600",
          )}
        >
          €{plan.setupFeeEur} one-time setup · {plan.customerCap}
        </p>
      </div>

      <ul className="mt-6 flex flex-1 flex-col gap-3">
        {plan.features.map((feat) => (
          <li
            key={feat}
            className={cn(
              "flex items-start gap-2 text-sm leading-relaxed",
              highlighted ? "text-cream/90" : "text-neutral-900",
            )}
          >
            <Check
              className={cn(
                "mt-0.5 h-4 w-4 shrink-0",
                highlighted ? "text-amber-500" : "text-green-900",
              )}
              aria-hidden="true"
            />
            <span>{feat}</span>
          </li>
        ))}
      </ul>

      <div className="mt-7">
        <LandingButton
          href={`/signup?plan=${plan.id}`}
          variant={highlighted ? "secondary" : "primary"}
          size="md"
          className={cn(
            "w-full",
            highlighted &&
              cn(
                "border-cream bg-cream text-green-900",
                "hover:border-amber-500 hover:bg-amber-500 hover:text-neutral-900",
              ),
          )}
        >
          {PRICING_CTA_LABEL}
        </LandingButton>
      </div>
    </article>
  );
}

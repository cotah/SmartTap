import { Check } from "lucide-react";
import * as React from "react";

import type { Plan } from "@/lib/landing/pricing-plans";
import { PRICING_CTA_LABEL } from "@/lib/landing/pricing-plans";
import { cn } from "@/lib/utils";

import { LandingButton } from "../button";

/**
 * Single pricing card (Dark Electric).
 *
 * Two visual variants driven by `plan.highlight`:
 * - Default: raised dark surface, subtle border, ghost CTA
 * - Highlighted ("Most popular"): cyan border + glow + faint cyan gradient,
 *   cyan badge, cyan price, filled cyan CTA, slightly lifted
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
          ? "border-electric-cyan bg-gradient-to-b from-electric-surface-2 to-electric-surface text-electric-text shadow-[0_0_40px_rgba(0,212,255,0.18)] ring-1 ring-electric-cyan/40 md:scale-[1.02]"
          : "border-electric-border bg-electric-surface text-electric-text hover:border-electric-cyan/40",
      )}
    >
      {highlighted && (
        <span
          className={cn(
            "absolute -top-3 left-1/2 -translate-x-1/2 rounded-full",
            "bg-electric-cyan px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.1em] text-electric-bg",
            "shadow-[0_0_16px_rgba(0,212,255,0.6)]",
          )}
        >
          ★ Most popular
        </span>
      )}

      <header className="flex flex-col gap-1">
        <h3 className="font-display text-2xl font-semibold leading-tight tracking-tight text-electric-text">
          {plan.name}
        </h3>
        <p className="text-sm text-electric-text-muted">{plan.tagline}</p>
      </header>

      <div className="mt-6 flex flex-col gap-1">
        <p className="flex items-baseline gap-1">
          <span
            className={cn(
              "font-display text-[40px] font-semibold leading-none tracking-tight",
              highlighted ? "text-electric-cyan" : "text-electric-text",
            )}
          >
            €{plan.monthlyEur}
          </span>
          <span className="text-sm text-electric-text-muted">/month</span>
        </p>
        <p className="text-[13px] text-electric-text-muted">
          €{plan.setupFeeEur} one-time setup · {plan.customerCap}
        </p>
      </div>

      <ul className="mt-6 flex flex-1 flex-col gap-3">
        {plan.features.map((feat) => (
          <li
            key={feat}
            className="flex items-start gap-2 text-sm leading-relaxed text-electric-text-muted"
          >
            <Check
              className="mt-0.5 h-4 w-4 shrink-0 text-electric-cyan"
              aria-hidden="true"
            />
            <span>{feat}</span>
          </li>
        ))}
      </ul>

      <div className="mt-7">
        <LandingButton
          href={`/signup?plan=${plan.id}`}
          variant={highlighted ? "primary" : "secondary"}
          size="md"
          className="w-full"
        >
          {PRICING_CTA_LABEL}
        </LandingButton>
      </div>
    </article>
  );
}

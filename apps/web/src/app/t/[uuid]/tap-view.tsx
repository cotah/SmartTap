import type { TapResponse } from "@/lib/api";

import { GoogleReviewButton } from "./google-review-button";
import { OptInForm } from "./opt-in-form";

interface Props {
  data: TapResponse;
}

/**
 * Customer-facing view rendered after a tap on /t/[uuid].
 *
 * Hierarchy (mobile-first, above-the-fold):
 *  1. Compact header — logo + tenant name
 *  2. (Optional) reward code strip when reward_available
 *  3. DOMINANT Google Review CTA (the page's primary KPI)
 *  4. Compact stamp progress strip + campaign pill
 *
 * Below the fold:
 *  5. Opt-in form (only when customer === null)
 *  6. Footer
 *
 * The Review button is intentionally the largest interactive element on
 * the page — review volume is the single biggest KPI per LANDING-SPEC §1.
 * Loyalty (stamps + opt-in) is real but secondary: the customer who came
 * to redeem a reward sees the code in a slim strip above the CTA, the
 * customer who just got a stamp sees the count as a compact pill below.
 */
export function TapView({ data }: Props) {
  const {
    tenant,
    customer,
    reward_state,
    reward_available,
    active_campaign,
  } = data;
  const bg = tenant.primary_color;
  const accent = tenant.accent_color;

  return (
    <main
      className="min-h-dvh text-brand-off-white"
      style={{ backgroundColor: bg }}
    >
      <div className="mx-auto flex min-h-dvh max-w-md flex-col gap-5 px-5 py-5 sm:gap-6 sm:py-7">
        {/* 1. Header — compact, never dominates */}
        <header className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 overflow-hidden">
            {tenant.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element -- next/image with remotePatterns lands in S1-W6
              <img
                src={tenant.logo_url}
                alt={tenant.name}
                className="h-10 w-10 shrink-0 rounded-full bg-white/10 object-contain"
              />
            ) : null}
            <div className="flex min-w-0 flex-col">
              <p className="truncate font-display text-lg leading-tight">
                {tenant.name}
              </p>
              <p className="text-[10px] font-medium uppercase tracking-[0.18em] opacity-70">
                Tapped in
              </p>
            </div>
          </div>
        </header>

        {/* 2. Reward-ready strip (only when applicable) — sits ABOVE the
             review button as a quiet context line so the Review CTA stays
             dominant even when there's something to redeem. */}
        {reward_available ? (
          <div
            className="flex items-center justify-between gap-3 rounded-xl bg-white/95 px-4 py-3 text-brand-black"
            style={{ borderLeft: `4px solid ${accent}` }}
          >
            <div className="min-w-0">
              <p
                className="text-[10px] font-bold uppercase tracking-[0.18em]"
                style={{ color: accent }}
              >
                🎁 Reward ready
              </p>
              <p className="truncate text-sm font-semibold">
                {reward_available.description}
              </p>
            </div>
            <p
              className="shrink-0 font-mono text-xl font-bold tracking-widest"
              aria-label={`Validation code ${reward_available.validation_code}`}
            >
              {reward_available.validation_code.replace(
                /(\d{3})(\d{3})/,
                "$1 $2",
              )}
            </p>
          </div>
        ) : null}

        {/* 3. DOMINANT Google Review CTA — above the fold, always */}
        {tenant.google_review_url ? (
          <GoogleReviewButton
            url={tenant.google_review_url}
            tenantSlug={tenant.slug}
            accentColor={accent}
          />
        ) : null}

        {/* 4. Compact stamp strip + active campaign pill */}
        <StampStrip
          state={reward_state}
          accent={accent}
          stampAwarded={data.stamp_awarded}
          stampDelta={data.stamps_awarded_count}
        />

        {active_campaign ? (
          <div
            className="rounded-full px-3 py-1.5 text-center text-xs font-semibold uppercase tracking-wide"
            style={{ backgroundColor: accent, color: bg }}
          >
            {active_campaign.multiplier}× stamps today · {active_campaign.name}
          </div>
        ) : null}

        {/* 5. Below-fold: opt-in form (only when not opted in yet) */}
        {customer === null ? (
          <div className="mt-2">
            <OptInForm
              tenantId={tenant.id}
              tenantName={tenant.name}
              accentColor={accent}
            />
          </div>
        ) : null}

        {/* Spacer + footer */}
        <div className="flex-1" />
        <footer className="text-center text-[11px] opacity-60">
          Powered by SmartTap · <a href="/privacy">Privacy</a> ·{" "}
          <a href="/data-request">Delete my data</a>
        </footer>
      </div>
    </main>
  );
}

/**
 * Single-line stamp counter — replaces the previous 5xl number block.
 * Designed to sit immediately under the Review CTA without competing
 * with it visually.
 */
function StampStrip({
  state,
  accent,
  stampAwarded,
  stampDelta,
}: {
  state: TapResponse["reward_state"];
  accent: string;
  stampAwarded: boolean;
  stampDelta: number;
}) {
  return (
    <div className="rounded-xl bg-white/10 px-4 py-3 backdrop-blur-sm">
      <div className="flex items-baseline justify-between gap-3">
        <p className="flex items-baseline gap-2">
          {stampAwarded ? (
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
              style={{ backgroundColor: accent, color: "#1A1A1A" }}
            >
              +{stampDelta > 1 ? stampDelta : 1} stamp
            </span>
          ) : null}
          <span className="font-display text-xl leading-none">
            {state.current_stamps}
            <span className="text-sm opacity-70"> / {state.stamps_for_reward}</span>
          </span>
        </p>
        <p className="text-xs opacity-70">
          {state.stamps_remaining === 0
            ? "Reward unlocked"
            : `${state.stamps_remaining} to reward`}
        </p>
      </div>
      <div
        className="mt-2 h-1.5 overflow-hidden rounded-full"
        style={{ backgroundColor: "rgba(255,255,255,0.18)" }}
      >
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${state.progress_percent}%`,
            backgroundColor: accent,
          }}
        />
      </div>
    </div>
  );
}

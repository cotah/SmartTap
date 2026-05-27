"use client";

import { motion } from "framer-motion";
import { Gift, Stamp } from "lucide-react";

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
 *  1. Compact header — logo or tenant name
 *  2. Hero greeting — "Welcome back, {name}" / "Welcome to {tenant}"
 *  3. (Optional) reward-ready strip when reward_available
 *  4. DOMINANT Google Review CTA (the page's primary KPI)
 *  5. Stamp bento card — 5-col grid + progress bar
 *  6. (Optional) active campaign pill
 *
 * Below the fold:
 *  7. Opt-in form (only when customer === null)
 *  8. Footer
 *
 * The Review button remains the largest interactive element on the page —
 * review volume is the single biggest KPI per LANDING-SPEC §1. Visual
 * language (light parchment canvas, white cards, ambient green-tinted
 * shadows) comes from the "Irish Heritage Tech" Stitch design refresh.
 */
export function TapView({ data }: Props) {
  const {
    tenant,
    customer,
    reward_state,
    reward_available,
    active_campaign,
  } = data;
  const accent = tenant.accent_color;

  const customerName = customer?.name?.trim() || null;
  const greeting = customer
    ? customerName
      ? `Welcome back, ${customerName}`
      : "Welcome back"
    : `Welcome to ${tenant.name}`;

  return (
    <main className="relative min-h-dvh overflow-x-hidden bg-brand-off-white text-brand-black">
      {/* Ambient top glow — subtle physical feel */}
      <div className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-64 bg-gradient-to-b from-brand-green/5 to-transparent" />

      <div className="mx-auto flex min-h-dvh max-w-[480px] flex-col gap-6 px-4 py-8">
        {/* 1. Header */}
        <motion.header
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="flex flex-col items-center justify-center gap-3 pt-2"
        >
          {tenant.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- next/image with remotePatterns lands in S1-W6
            <img
              src={tenant.logo_url}
              alt={tenant.name}
              className="h-16 w-auto object-contain"
            />
          ) : (
            <p className="font-display text-xl text-brand-green">
              {tenant.name}
            </p>
          )}
        </motion.header>

        {/* 2. Hero greeting */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-center"
        >
          <h1 className="font-display text-[28px] leading-9 text-brand-green">
            {greeting}
          </h1>
          <p className="mx-auto mt-2 max-w-[280px] text-sm text-neutral-600">
            Check your loyalty progress below.
          </p>
        </motion.section>

        {/* 3. Reward-ready strip */}
        {reward_available ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="flex items-center justify-between gap-3 rounded-xl border-l-4 bg-white px-4 py-3 shadow-[0_4px_24px_rgba(27,77,62,0.04)]"
            style={{ borderLeftColor: accent }}
          >
            <div className="min-w-0">
              <p
                className="text-[10px] font-bold uppercase tracking-[0.18em]"
                style={{ color: accent }}
              >
                Reward ready
              </p>
              <p className="truncate text-sm font-semibold">
                {reward_available.description}
              </p>
            </div>
            <p
              className="shrink-0 font-mono text-xl font-bold tracking-widest text-brand-green"
              aria-label={`Validation code ${reward_available.validation_code}`}
            >
              {reward_available.validation_code.replace(
                /(\d{3})(\d{3})/,
                "$1 $2",
              )}
            </p>
          </motion.div>
        ) : null}

        {/* 4. DOMINANT Google Review CTA */}
        {tenant.google_review_url ? (
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <GoogleReviewButton
              url={tenant.google_review_url}
              tenantSlug={tenant.slug}
              accentColor={accent}
            />
            <p className="mt-3 text-center text-xs text-neutral-600/80">
              Your feedback helps the shop grow.
            </p>
          </motion.section>
        ) : null}

        {/* 5. Stamp bento card */}
        {reward_state.stamps_for_reward > 0 ? (
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="relative overflow-hidden rounded-xl border border-brand-green/5 bg-white p-6 shadow-[0_8px_32px_rgba(27,77,62,0.08)]"
          >
            {/* Decorative accent blur */}
            <div
              className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-20 blur-3xl"
              style={{ backgroundColor: accent }}
            />
            <StampCardHeader
              state={reward_state}
              stampAwarded={data.stamp_awarded}
              stampDelta={data.stamps_awarded_count}
              accent={accent}
            />
            <StampGrid
              current={reward_state.current_stamps}
              total={reward_state.stamps_for_reward}
              accent={accent}
            />
            {/* Progress bar */}
            <div className="relative z-10 mt-8 h-1.5 overflow-hidden rounded-full bg-neutral-300/30">
              <div
                className="absolute left-0 top-0 h-full rounded-full transition-all duration-500"
                style={{
                  width: `${reward_state.progress_percent}%`,
                  backgroundColor: accent,
                  boxShadow: `0 0 8px ${accent}99`,
                }}
              />
            </div>
          </motion.section>
        ) : null}

        {/* 6. Active campaign pill */}
        {active_campaign ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.35 }}
            className="rounded-full bg-brand-amber px-3 py-1.5 text-center text-xs font-bold uppercase tracking-wide text-brand-green"
          >
            {active_campaign.multiplier}× stamps today · {active_campaign.name}
          </motion.div>
        ) : null}

        {/* 7. Below-fold: opt-in form */}
        {customer === null ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <OptInForm tenantId={tenant.id} tenantName={tenant.name} />
          </motion.div>
        ) : null}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 0.5 }}
          className="mt-4 border-t border-neutral-300/30 py-6"
        >
          <div className="flex flex-col items-center justify-between gap-3 sm:flex-row">
            <span className="text-xs font-bold uppercase tracking-widest text-brand-green">
              Powered by SmartTap
            </span>
            <div className="flex gap-5">
              <a
                href="/terms"
                className="text-xs text-neutral-600/70 transition-colors hover:text-brand-amber"
              >
                Terms
              </a>
              <a
                href="/privacy"
                className="text-xs text-neutral-600/70 transition-colors hover:text-brand-amber"
              >
                Privacy
              </a>
              <a
                href="/data-request"
                className="text-xs text-neutral-600/70 transition-colors hover:text-brand-amber"
              >
                Delete my data
              </a>
            </div>
          </div>
        </motion.footer>
      </div>
    </main>
  );
}

function StampCardHeader({
  state,
  stampAwarded,
  stampDelta,
  accent,
}: {
  state: TapResponse["reward_state"];
  stampAwarded: boolean;
  stampDelta: number;
  accent: string;
}) {
  return (
    <div className="relative z-10 mb-8 flex items-end justify-between gap-3">
      <div className="min-w-0">
        <p className="text-[11px] font-bold uppercase tracking-widest text-brand-green/80">
          Reward Progress
        </p>
        <p className="mt-1 flex flex-wrap items-baseline gap-2">
          <span className="text-lg font-medium text-brand-black">
            {state.current_stamps} of {state.stamps_for_reward} collected
          </span>
          {stampAwarded ? (
            <span
              className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand-green"
              style={{ backgroundColor: accent }}
            >
              +{stampDelta > 1 ? stampDelta : 1}
            </span>
          ) : null}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1.5 rounded-full border border-brand-green/10 bg-brand-off-white px-3 py-1.5 text-[11px] font-medium text-brand-green">
        <Gift className="h-3.5 w-3.5" aria-hidden="true" />
        Reward at {state.stamps_for_reward}
      </div>
    </div>
  );
}

function StampGrid({
  current,
  total,
  accent,
}: {
  current: number;
  total: number;
  accent: string;
}) {
  const filled = Math.min(Math.max(current, 0), total);
  const slots = Array.from({ length: total }, (_, i) => i < filled);

  return (
    <div className="relative z-10 grid grid-cols-5 gap-x-3 gap-y-6">
      {slots.map((isFilled, i) =>
        isFilled ? (
          <div
            key={i}
            className="flex h-12 w-12 items-center justify-center justify-self-center rounded-full text-brand-green shadow-md transition-transform hover:scale-105"
            style={{ backgroundColor: accent }}
            aria-label="Stamp collected"
          >
            <Stamp className="h-5 w-5" aria-hidden="true" />
          </div>
        ) : (
          <div
            key={i}
            className="flex h-12 w-12 items-center justify-center justify-self-center rounded-full border border-dashed border-neutral-300 bg-brand-off-white/30 text-neutral-600 opacity-40"
            aria-label="Stamp not collected"
          >
            <Stamp className="h-5 w-5" aria-hidden="true" />
          </div>
        ),
      )}
    </div>
  );
}

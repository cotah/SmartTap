"use client";

import { Menu } from "lucide-react";

import type { TrialStatus } from "@/lib/api";

import { SignOutButton } from "./sign-out-button";

interface Props {
  tenantName: string;
  email: string | null;
  trialStatus: TrialStatus;
  trialEndsAt: string | null;
  onMenuClick: () => void;
}

export function TopBar({
  tenantName,
  email,
  trialStatus,
  trialEndsAt,
  onMenuClick,
}: Props) {
  return (
    <header className="flex items-center justify-between border-b border-neutral-300/30 bg-brand-off-white px-4 py-4 md:px-10">
      <div className="flex items-center gap-3 md:gap-4">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Open menu"
          className="rounded-lg p-1 text-brand-green hover:bg-brand-green/5 md:hidden"
        >
          <Menu className="h-6 w-6" aria-hidden="true" />
        </button>
        <h1 className="truncate font-display text-xl leading-tight text-brand-black sm:text-2xl md:text-3xl">
          {tenantName}
        </h1>
        <TrialPill status={trialStatus} trialEndsAt={trialEndsAt} />
      </div>
      <div className="flex shrink-0 items-center gap-4">
        {email ? (
          <span className="hidden text-sm text-neutral-600 md:inline">
            {email}
          </span>
        ) : null}
        <SignOutButton />
      </div>
    </header>
  );
}

/**
 * Compact informational pill in the top bar. Only renders when status is
 * `active` and the trial ends within 14 days — gives ambient awareness of
 * remaining trial days without nagging. Critical states (`expiring_soon`,
 * `expired`, `inactive`) are still surfaced by TrialBanner above.
 */
function TrialPill({
  status,
  trialEndsAt,
}: {
  status: TrialStatus;
  trialEndsAt: string | null;
}) {
  if (status !== "active") return null;
  if (!trialEndsAt) return null;

  const target = new Date(trialEndsAt).getTime();
  if (Number.isNaN(target)) return null;

  const diff = target - Date.now();
  if (diff <= 0) return null;

  const days = Math.max(1, Math.ceil(diff / (1000 * 60 * 60 * 24)));
  if (days > 14) return null;

  const dayText = days === 1 ? "1 day" : `${days} days`;
  return (
    <span className="hidden rounded-full bg-brand-amber/15 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-brand-green sm:inline-block">
      Trial · {dayText} left
    </span>
  );
}

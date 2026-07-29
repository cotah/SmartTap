"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { Menu } from "lucide-react";

import type { TrialStatus } from "@/lib/api";

import { SignOutButton } from "./sign-out-button";
import { switchTenantAction } from "./tenant-actions";

interface Props {
  tenantName: string;
  email: string | null;
  trialStatus: TrialStatus;
  trialEndsAt: string | null;
  /** All memberships; the switcher only renders when there is more than one. */
  tenants: Array<{ id: string; name: string }>;
  activeTenantId: string;
  onMenuClick: () => void;
}

export function TopBar({
  tenantName,
  email,
  trialStatus,
  trialEndsAt,
  tenants,
  activeTenantId,
  onMenuClick,
}: Props) {
  const router = useRouter();
  const [switching, startTransition] = useTransition();

  function handleSwitch(tenantId: string) {
    if (tenantId === activeTenantId) return;
    startTransition(async () => {
      const res = await switchTenantAction(tenantId);
      if (res.ok) router.refresh();
    });
  }

  return (
    <header className="flex items-center justify-between border-b border-electric-border bg-electric-bg px-4 py-4 md:px-10">
      <div className="flex items-center gap-3 md:gap-4">
        <button
          type="button"
          onClick={onMenuClick}
          aria-label="Open menu"
          className="rounded-lg p-1 text-electric-cyan hover:bg-electric-surface-2 md:hidden"
        >
          <Menu className="h-6 w-6" aria-hidden="true" />
        </button>
        {tenants.length > 1 ? (
          <select
            value={activeTenantId}
            onChange={(e) => handleSwitch(e.target.value)}
            disabled={switching}
            aria-label="Switch business"
            className="max-w-[50vw] truncate rounded-lg border border-electric-border bg-electric-surface px-2 py-1 font-display text-lg font-semibold text-electric-text focus:border-electric-cyan focus:outline-none disabled:opacity-60 sm:text-xl md:text-2xl"
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        ) : (
          <h1 className="truncate font-display text-xl font-semibold leading-tight text-electric-text sm:text-2xl md:text-3xl">
            {tenantName}
          </h1>
        )}
        <TrialPill status={trialStatus} trialEndsAt={trialEndsAt} />
      </div>
      <div className="flex shrink-0 items-center gap-4">
        {email ? (
          <span className="hidden text-sm text-electric-text-muted md:inline">
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
    <span className="hidden rounded-full bg-electric-cyan/15 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-electric-cyan sm:inline-block">
      Trial · {dayText} left
    </span>
  );
}

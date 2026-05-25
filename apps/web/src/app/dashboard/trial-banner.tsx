import Link from "next/link";

import type { TrialStatus } from "@/lib/api";

interface Props {
  status: TrialStatus;
  trialEndsAt: string | null;
}

/**
 * Top-of-dashboard alert about trial state. Renders only for the three states
 * the user cares about; returns null for `active` (silent) and `inactive`
 * (handled separately as cancellation messaging).
 *
 * - expiring_soon → amber, soft nudge with day countdown
 * - expired       → red, blocking copy ("can't make changes")
 * - subscribed    → null (no need to nag paying customers)
 */
export function TrialBanner({ status, trialEndsAt }: Props) {
  if (status === "active" || status === "subscribed") return null;

  if (status === "expiring_soon") {
    const days = daysUntil(trialEndsAt);
    const dayText = days === 1 ? "1 day" : `${days} days`;
    return (
      <Banner tone="amber">
        <span>
          Your free trial ends in <strong>{dayText}</strong>. Upgrade now to keep
          full access.
        </span>
        <Cta href="/dashboard/billing" tone="amber">
          See plans
        </Cta>
      </Banner>
    );
  }

  if (status === "expired") {
    return (
      <Banner tone="red">
        <span>
          Your free trial has ended. You can still view your data, but{" "}
          <strong>changes are locked</strong> until you upgrade.
        </span>
        <Cta href="/dashboard/billing" tone="red">
          Upgrade now
        </Cta>
      </Banner>
    );
  }

  // inactive — subscription was cancelled or payment failed permanently
  return (
    <Banner tone="red">
      <span>
        Your subscription is inactive. <strong>Changes are locked</strong> until
        you update payment.
      </span>
      <Cta href="/dashboard/billing" tone="red">
        Manage billing
      </Cta>
    </Banner>
  );
}

function Banner({
  tone,
  children,
}: {
  tone: "amber" | "red";
  children: React.ReactNode;
}) {
  const styles =
    tone === "amber"
      ? "border-brand-amber/30 bg-brand-amber/10 text-brand-black"
      : "border-red-200 bg-red-50 text-red-900";
  return (
    <div
      role="alert"
      className={`flex flex-col items-start gap-3 border-b px-4 py-3 text-sm md:flex-row md:items-center md:justify-between md:px-6 ${styles}`}
    >
      <div className="flex-1">{children}</div>
    </div>
  );
}

function Cta({
  href,
  tone,
  children,
}: {
  href: string;
  tone: "amber" | "red";
  children: React.ReactNode;
}) {
  const styles =
    tone === "amber"
      ? "bg-brand-amber text-brand-black"
      : "bg-red-600 text-white";
  return (
    <Link
      href={href}
      className={`rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-wide ${styles}`}
    >
      {children}
    </Link>
  );
}

function daysUntil(iso: string | null): number {
  if (!iso) return 0;
  const target = new Date(iso).getTime();
  if (Number.isNaN(target)) return 0;
  const diff = target - Date.now();
  if (diff <= 0) return 0;
  return Math.max(1, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

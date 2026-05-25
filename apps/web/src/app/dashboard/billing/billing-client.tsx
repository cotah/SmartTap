"use client";

import { useState, useTransition } from "react";

import type { BillingPlanId, SubscriptionInfo } from "@/lib/api";

import { openPortalAction, startCheckoutAction } from "./actions";

interface PlanDef {
  id: BillingPlanId;
  name: string;
  priceMonthly: number;
  setupFee: number;
  customers: string;
  features: string[];
  highlight?: boolean;
}

// Pricing v2 from CLAUDE.md. Single source of truth lives in Stripe (price
// IDs in backend env); this list is for display only.
const PLANS: PlanDef[] = [
  {
    id: "review",
    name: "SmartReview",
    priceMonthly: 29,
    setupFee: 49,
    customers: "Up to 200 customers",
    features: ["1-tap Google Reviews", "Tap analytics", "Email support"],
  },
  {
    id: "loyalty",
    name: "SmartLoyalty",
    priceMonthly: 59,
    setupFee: 79,
    customers: "Up to 500 customers",
    features: [
      "Everything in Review",
      "Digital stamp cards",
      "Reward redemption",
      "Customer list & filters",
    ],
    highlight: true,
  },
  {
    id: "pro",
    name: "SmartPro",
    priceMonthly: 99,
    setupFee: 149,
    customers: "Unlimited customers",
    features: [
      "Everything in Loyalty",
      "WhatsApp campaigns",
      "AI review responses",
      "Priority support",
    ],
  },
  {
    id: "network",
    name: "SmartNetwork",
    priceMonthly: 179,
    setupFee: 299,
    customers: "Multi-location",
    features: [
      "Everything in Pro",
      "Multiple branches",
      "White-label option",
      "Dedicated success manager",
    ],
  },
];

type Banner = { kind: "success" | "error"; text: string } | null;

interface Props {
  subscription: SubscriptionInfo;
}

export function BillingClient({ subscription }: Props) {
  const [banner, setBanner] = useState<Banner>(null);
  const [pendingPlan, setPendingPlan] = useState<BillingPlanId | "portal" | null>(null);
  const [, startTransition] = useTransition();

  const hasSubscription = subscription.has_subscription;

  function handlePlanClick(plan: BillingPlanId) {
    // If the tenant already has a subscription, route plan changes through the
    // Stripe Portal — that avoids charging the setup fee a second time and
    // lets Stripe pro-rate the swap.
    if (hasSubscription) {
      handleOpenPortal();
      return;
    }
    setBanner(null);
    setPendingPlan(plan);
    startTransition(async () => {
      const result = await startCheckoutAction(plan);
      if (result.ok) {
        window.location.href = result.url;
        return;
      }
      setPendingPlan(null);
      setBanner({ kind: "error", text: result.message });
    });
  }

  function handleOpenPortal() {
    setBanner(null);
    setPendingPlan("portal");
    startTransition(async () => {
      const result = await openPortalAction();
      if (result.ok) {
        window.location.href = result.url;
        return;
      }
      setPendingPlan(null);
      setBanner({ kind: "error", text: result.message });
    });
  }

  return (
    <div className="space-y-8">
      <SubscriptionStatus subscription={subscription} />

      {banner ? (
        <div
          role="status"
          className={`rounded-lg px-3 py-2 text-sm ${
            banner.kind === "success"
              ? "bg-brand-green/10 text-brand-green"
              : "bg-red-50 text-red-700"
          }`}
        >
          {banner.text}
        </div>
      ) : null}

      {hasSubscription ? (
        <section className="rounded-2xl border border-brand-black/10 bg-white p-5 shadow-sm">
          <div className="flex flex-col items-start gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="font-display text-lg">Manage subscription</p>
              <p className="text-sm text-brand-black/60">
                Change plan, update card, download invoices, or cancel — handled
                securely by Stripe.
              </p>
            </div>
            <button
              type="button"
              onClick={handleOpenPortal}
              disabled={pendingPlan !== null}
              className="rounded-full bg-brand-black px-5 py-2 text-sm font-semibold text-brand-off-white disabled:opacity-60"
            >
              {pendingPlan === "portal" ? "Opening…" : "Open billing portal"}
            </button>
          </div>
        </section>
      ) : null}

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand-black/70">
          Plans
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {PLANS.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              currentPlan={subscription.plan}
              hasSubscription={hasSubscription}
              isFoundingMember={subscription.is_founding_member}
              pending={pendingPlan === plan.id}
              disabled={pendingPlan !== null}
              onClick={() => handlePlanClick(plan.id)}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function SubscriptionStatus({ subscription }: { subscription: SubscriptionInfo }) {
  const statusLabel = deriveStatusLabel(subscription);
  const nextCharge = formatDate(subscription.current_period_end);

  return (
    <section className="rounded-2xl border border-brand-black/10 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-black/55">
            Current plan
          </p>
          <p className="font-display text-2xl">{planDisplayName(subscription.plan)}</p>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <StatusBadge tone={statusLabel.tone}>{statusLabel.text}</StatusBadge>
            {subscription.is_founding_member ? (
              <StatusBadge tone="amber">
                Founding Member · €29/mo for life
              </StatusBadge>
            ) : null}
            {subscription.cancel_at_period_end ? (
              <StatusBadge tone="red">Cancels at period end</StatusBadge>
            ) : null}
          </div>
        </div>
        <div className="text-sm text-brand-black/60">
          {nextCharge ? (
            <p>
              <span className="font-semibold text-brand-black">Next charge:</span>{" "}
              {nextCharge}
            </p>
          ) : subscription.trial_ends_at ? (
            <p>
              <span className="font-semibold text-brand-black">Trial ends:</span>{" "}
              {formatDate(subscription.trial_ends_at)}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function PlanCard({
  plan,
  currentPlan,
  hasSubscription,
  isFoundingMember,
  pending,
  disabled,
  onClick,
}: {
  plan: PlanDef;
  currentPlan: SubscriptionInfo["plan"];
  hasSubscription: boolean;
  isFoundingMember: boolean;
  pending: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const isCurrent = currentPlan === plan.id;
  // Founding members keep €29 forever regardless of which plan card we render
  // the price block for — but we only show the "effective price" note on the
  // plan they actually hold, so the cards remain honest about list prices.
  const priceLine = isFoundingMember && isCurrent
    ? "€29 / month (locked)"
    : `€${plan.priceMonthly} / month`;

  const buttonLabel = (() => {
    if (pending) return "Loading…";
    if (isCurrent) return "Current plan";
    if (hasSubscription) return "Switch to this plan";
    return "Choose plan";
  })();

  return (
    <article
      className={`flex flex-col rounded-2xl border bg-white p-5 shadow-sm ${
        plan.highlight ? "border-brand-green" : "border-brand-black/10"
      } ${isCurrent ? "ring-2 ring-brand-green ring-offset-2" : ""}`}
    >
      <header className="space-y-1">
        {plan.highlight ? (
          <p className="text-xs font-semibold uppercase tracking-wide text-brand-green">
            Most popular
          </p>
        ) : null}
        <h3 className="font-display text-xl">{plan.name}</h3>
        <p className="text-sm text-brand-black/60">{plan.customers}</p>
      </header>

      <div className="mt-4 space-y-1">
        <p className="font-display text-2xl">{priceLine}</p>
        {!isFoundingMember || !isCurrent ? (
          <p className="text-xs text-brand-black/55">+ €{plan.setupFee} one-time setup</p>
        ) : null}
      </div>

      <ul className="mt-4 flex-1 space-y-1.5 text-sm">
        {plan.features.map((feature) => (
          <li key={feature} className="flex items-start gap-2">
            <span aria-hidden className="mt-1 text-brand-green">✓</span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={onClick}
        disabled={disabled || isCurrent}
        className={`mt-5 rounded-full px-4 py-2 text-sm font-semibold disabled:opacity-60 ${
          isCurrent
            ? "border border-brand-black/20 bg-transparent text-brand-black"
            : "bg-brand-green text-brand-off-white"
        }`}
      >
        {buttonLabel}
      </button>
    </article>
  );
}

function StatusBadge({
  tone,
  children,
}: {
  tone: "green" | "amber" | "red" | "neutral";
  children: React.ReactNode;
}) {
  const styles: Record<typeof tone, string> = {
    green: "bg-brand-green/10 text-brand-green",
    amber: "bg-brand-amber/10 text-brand-amber",
    red: "bg-red-50 text-red-700",
    neutral: "bg-brand-black/5 text-brand-black/70",
  };
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${styles[tone]}`}
    >
      {children}
    </span>
  );
}

type StatusTone = "green" | "amber" | "red" | "neutral";

function deriveStatusLabel(
  subscription: SubscriptionInfo,
): { text: string; tone: StatusTone } {
  if (subscription.plan === "trial" && subscription.is_active) {
    return { text: "Trial", tone: "amber" };
  }
  if (!subscription.is_active) {
    return { text: "Inactive", tone: "red" };
  }
  // Stripe-side status — only available once we have a subscription.
  switch (subscription.status) {
    case "active":
      return { text: "Active", tone: "green" };
    case "trialing":
      return { text: "Trial", tone: "amber" };
    case "past_due":
    case "unpaid":
      return { text: "Payment failed", tone: "red" };
    case "canceled":
      return { text: "Canceled", tone: "red" };
    default:
      return { text: "Active", tone: "green" };
  }
}

function planDisplayName(plan: SubscriptionInfo["plan"]): string {
  switch (plan) {
    case "trial":
      return "Trial";
    case "review":
      return "SmartReview";
    case "loyalty":
      return "SmartLoyalty";
    case "pro":
      return "SmartPro";
    case "network":
      return "SmartNetwork";
  }
}

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString("en-IE", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

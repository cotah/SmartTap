import {
  AlertTriangle,
  CalendarCheck,
  type LucideIcon,
  Smartphone,
  Stamp,
  Star,
  Users,
} from "lucide-react";

import type { DashboardOverview } from "@/lib/api";

interface Props {
  overview: DashboardOverview;
}

export function OverviewCards({ overview }: Props) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
      <MetricCard
        label="Total customers"
        value={overview.customers_total}
        hint="All-time signups"
        icon={Users}
        accent="cyan"
        size="hero"
        className="md:col-span-2"
      />
      <MetricCard
        label="Loyalty visits today"
        value={overview.loyalty_visits_today}
        hint="Stamp taps today"
        icon={CalendarCheck}
        accent="fuchsia"
      />
      <MetricCard
        label="Taps this week"
        value={overview.taps_week}
        hint="Last 7 days"
        icon={Smartphone}
        accent="violet"
      />
      <MetricCard
        label="Reviews"
        value={overview.reviews_month}
        hint="Last 30 days"
        icon={Star}
        accent="amber"
      />
      <MetricCard
        label="At risk"
        value={overview.customers_at_risk}
        hint="No visit in 30+ days"
        icon={AlertTriangle}
        tone="error"
      />
      <MetricCard
        label="Active stamps"
        value={overview.active_stamps_total}
        hint="Across all customers"
        icon={Stamp}
        accent="emerald"
      />
    </div>
  );
}

type Accent = "cyan" | "violet" | "amber" | "emerald" | "fuchsia";

// Per-metric icon badge tints. These live as full literal strings so Tailwind's
// JIT keeps them. They only tint the icon plate on the dark surface (large
// element, never small text), so the cyan-on-light contrast rule doesn't apply.
const ACCENT_BADGE: Record<Accent, string> = {
  cyan: "bg-electric-cyan/15 text-electric-cyan",
  violet: "bg-violet-500/15 text-violet-300",
  amber: "bg-amber-500/15 text-amber-300",
  emerald: "bg-emerald-500/15 text-emerald-300",
  fuchsia: "bg-fuchsia-500/15 text-fuchsia-300",
};

interface MetricCardProps {
  label: string;
  value: number;
  hint: string;
  icon: LucideIcon;
  accent?: Accent;
  size?: "default" | "hero";
  tone?: "default" | "error";
  className?: string;
}

function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = "cyan",
  size = "default",
  tone = "default",
  className = "",
}: MetricCardProps) {
  const isError = tone === "error";
  const isHero = size === "hero";

  const containerStyles = isError
    ? "bg-red-500/10 border-red-500/30"
    : isHero
      ? "bg-electric-surface border-electric-cyan/40 shadow-[0_0_30px_rgba(0,212,255,0.1)]"
      : "bg-electric-surface border-electric-border";
  const iconStyles = isError ? "bg-red-500/15 text-red-300" : ACCENT_BADGE[accent];
  const valueColor = isError
    ? "text-red-300"
    : isHero
      ? "text-electric-cyan"
      : "text-electric-text";
  const valueSize = isHero
    ? "text-5xl sm:text-6xl"
    : "text-3xl sm:text-4xl";
  const hintColor = isError ? "text-red-300/70" : "text-electric-text-muted";

  return (
    <div
      className={`relative flex flex-col justify-between gap-6 overflow-hidden rounded-xl border p-6 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.5)] ${containerStyles} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-electric-text-muted">
            {label}
          </p>
          <p
            className={`mt-2 font-display font-semibold leading-none ${valueSize} ${valueColor}`}
          >
            {value.toLocaleString()}
          </p>
        </div>
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${iconStyles}`}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </div>
      <p className={`border-t border-electric-border pt-3 text-xs ${hintColor}`}>
        {hint}
      </p>
    </div>
  );
}

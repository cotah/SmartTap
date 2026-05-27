import {
  AlertTriangle,
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
        size="hero"
        className="md:col-span-2"
      />
      <MetricCard
        label="Taps this week"
        value={overview.taps_week}
        hint="Last 7 days"
        icon={Smartphone}
      />
      <MetricCard
        label="Reviews"
        value={overview.reviews_month}
        hint="Last 30 days"
        icon={Star}
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
      />
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: number;
  hint: string;
  icon: LucideIcon;
  size?: "default" | "hero";
  tone?: "default" | "error";
  className?: string;
}

function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
  size = "default",
  tone = "default",
  className = "",
}: MetricCardProps) {
  const isError = tone === "error";
  const isHero = size === "hero";

  const containerStyles = isError
    ? "bg-red-50 border-red-200/60"
    : "bg-white border-brand-green/10";
  const iconStyles = isError
    ? "bg-red-100 text-red-700"
    : "bg-brand-off-white text-brand-green";
  const valueColor = isError
    ? "text-red-700"
    : isHero
      ? "text-brand-green"
      : "text-brand-black";
  const valueSize = isHero
    ? "text-5xl sm:text-6xl"
    : "text-3xl sm:text-4xl";
  const hintColor = isError ? "text-red-700/70" : "text-neutral-600";

  return (
    <div
      className={`relative flex flex-col justify-between gap-6 overflow-hidden rounded-xl border p-6 shadow-[0_4px_12px_rgba(27,77,62,0.04)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(27,77,62,0.08)] ${containerStyles} ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-neutral-600">
            {label}
          </p>
          <p
            className={`mt-2 font-display leading-none ${valueSize} ${valueColor}`}
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
      <p className={`border-t border-neutral-300/20 pt-3 text-xs ${hintColor}`}>
        {hint}
      </p>
    </div>
  );
}

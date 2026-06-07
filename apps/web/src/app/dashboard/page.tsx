import {
  ArrowRight,
  CreditCard,
  Gift,
  Layers,
  type LucideIcon,
  Megaphone,
  Settings,
  Tag,
  Users,
} from "lucide-react";
import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { ActivityChart } from "./activity-chart";
import { MonthlyReportButton } from "./monthly-report-button";
import { OverviewCards } from "./overview-cards";

interface QuickAction {
  href: string;
  title: string;
  sub: string;
  icon: LucideIcon;
}

const QUICK_ACTIONS: QuickAction[] = [
  {
    href: "/dashboard/customers",
    title: "Customers",
    sub: "View, filter, and export your customer list.",
    icon: Users,
  },
  {
    href: "/dashboard/segments",
    title: "Segments",
    sub: "Group customers by criteria for targeted campaigns.",
    icon: Layers,
  },
  {
    href: "/dashboard/tags",
    title: "NFC tags",
    sub: "Create and manage the stands on your counter.",
    icon: Tag,
  },
  {
    href: "/dashboard/reward",
    title: "Reward",
    sub: "Set the stamps required and the prize.",
    icon: Gift,
  },
  {
    href: "/dashboard/campaigns",
    title: "Campaigns",
    sub: "Double-stamp windows and reactivation pushes.",
    icon: Megaphone,
  },
  {
    href: "/dashboard/settings",
    title: "Settings",
    sub: "Brand colors and Google review URL.",
    icon: Settings,
  },
  {
    href: "/dashboard/billing",
    title: "Billing",
    sub: "Plan, invoices, and payment method.",
    icon: CreditCard,
  },
];

export default async function DashboardPage() {
  const ctx = await getDashboardContext();
  const api = getAuthApiClient();
  const [overview, timeseries] = await Promise.all([
    api.getOverview(),
    api.getTapsTimeseries(30),
  ]);

  const firstName = ctx.email?.split("@")[0] ?? "there";

  return (
    <div className="space-y-12">
      {/* Hero — Welcome */}
      <section>
        <p className="text-xs font-medium uppercase tracking-widest text-electric-text-muted">
          Welcome back,
        </p>
        <h1 className="mt-1 font-display text-3xl font-semibold leading-tight text-electric-cyan sm:text-4xl">
          {firstName}
        </h1>
      </section>

      {/* Overview */}
      <section>
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="font-display text-2xl font-semibold text-electric-text">Overview</h2>
          <MonthlyReportButton />
        </div>
        <OverviewCards overview={overview} />
        <div className="mt-4">
          <ActivityChart points={timeseries.points} />
        </div>
      </section>

      {/* Quick Actions */}
      <section>
        <h2 className="mb-6 font-display text-2xl font-semibold text-electric-text">
          Quick actions
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {QUICK_ACTIONS.map((action) => (
            <ActionCard key={action.href} {...action} />
          ))}
        </div>
      </section>
    </div>
  );
}

function ActionCard({ href, title, sub, icon: Icon }: QuickAction) {
  return (
    <Link
      href={href}
      className="group flex flex-col items-start gap-4 rounded-xl border border-electric-border bg-electric-surface p-6 transition-all hover:-translate-y-0.5 hover:border-electric-cyan/40 hover:bg-electric-surface-2"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-electric-surface-2 text-electric-cyan transition-colors group-hover:bg-electric-cyan group-hover:text-electric-bg">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </div>
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-electric-text">
          {title}
        </h3>
        <p className="mt-1 text-sm text-electric-text-muted">{sub}</p>
      </div>
      <ArrowRight
        className="mt-auto self-end h-5 w-5 text-electric-text-muted transition-colors group-hover:text-electric-cyan"
        aria-hidden="true"
      />
    </Link>
  );
}

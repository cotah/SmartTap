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
  const overview = await api.getOverview();

  const firstName = ctx.email?.split("@")[0] ?? "there";

  return (
    <div className="space-y-12">
      {/* Hero — Welcome */}
      <section>
        <p className="text-xs font-medium uppercase tracking-widest text-neutral-600">
          Welcome back,
        </p>
        <h1 className="mt-1 font-display text-3xl leading-tight text-brand-green sm:text-4xl">
          {firstName}
        </h1>
      </section>

      {/* Overview */}
      <section>
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="font-display text-2xl text-brand-black">Overview</h2>
          <MonthlyReportButton />
        </div>
        <OverviewCards overview={overview} />
      </section>

      {/* Quick Actions */}
      <section>
        <h2 className="mb-6 font-display text-2xl text-brand-black">
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
      className="group flex flex-col items-start gap-4 rounded-xl border border-neutral-300/30 bg-white p-6 shadow-[0_4px_12px_rgba(27,77,62,0.04)] transition-all hover:-translate-y-0.5 hover:bg-brand-green/5 hover:shadow-[0_8px_24px_rgba(27,77,62,0.08)]"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-brand-off-white text-brand-green transition-colors group-hover:bg-brand-green group-hover:text-white">
        <Icon className="h-6 w-6" aria-hidden="true" />
      </div>
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-brand-black">
          {title}
        </h3>
        <p className="mt-1 text-sm text-neutral-600">{sub}</p>
      </div>
      <ArrowRight
        className="mt-auto self-end h-5 w-5 text-neutral-600 transition-colors group-hover:text-brand-green"
        aria-hidden="true"
      />
    </Link>
  );
}

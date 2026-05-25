import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { OverviewCards } from "./overview-cards";

export default async function DashboardPage() {
  const ctx = await getDashboardContext();
  const api = getAuthApiClient();
  const overview = await api.getOverview();

  const firstName = ctx.email?.split("@")[0] ?? "there";

  return (
    <main className="space-y-8">
      <section>
        <p className="text-sm text-brand-black/60">Welcome back,</p>
        <h1 className="font-display text-3xl">{firstName}</h1>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand-black/70">
          Overview
        </h2>
        <OverviewCards overview={overview} />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand-black/70">
          Manage
        </h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <DashLink href="/dashboard/customers" title="Customers" sub="View, filter, export" />
          <DashLink href="/dashboard/reward" title="Reward" sub="Set stamps and prize" />
          <DashLink href="/dashboard/settings" title="Settings" sub="Brand and Google" />
        </div>
        <p className="mt-3 text-xs text-brand-black/50">
          Manage pages land in S2-W5 to S2-W7.
        </p>
      </section>
    </main>
  );
}

function DashLink({ href, title, sub }: { href: string; title: string; sub: string }) {
  return (
    <Link
      href={href}
      className="block rounded-2xl border border-brand-black/10 bg-white p-4 shadow-sm transition hover:border-brand-green"
    >
      <p className="font-display text-lg">{title}</p>
      <p className="text-sm text-brand-black/60">{sub}</p>
    </Link>
  );
}

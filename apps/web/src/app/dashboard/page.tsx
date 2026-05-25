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

      <section className="rounded-2xl border border-brand-green/30 bg-brand-green/5 p-4">
        <div className="flex flex-col items-start gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-display text-lg">Customer at the counter?</p>
            <p className="text-sm text-brand-black/60">
              Validate a 6-digit reward code in seconds.
            </p>
          </div>
          <Link
            href="/dashboard/redeem"
            className="rounded-full bg-brand-green px-5 py-2 text-sm font-semibold text-brand-off-white"
          >
            Redeem reward
          </Link>
        </div>
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

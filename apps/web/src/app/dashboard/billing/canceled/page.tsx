import Link from "next/link";

import { getDashboardContext } from "@/lib/dashboard-data";

export default async function BillingCanceledPage() {
  await getDashboardContext();

  return (
    <main className="mx-auto max-w-xl space-y-6 py-8 text-center">
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-electric-text-muted">
          Checkout canceled
        </p>
        <h1 className="font-display text-3xl">No charge was made</h1>
        <p className="text-sm text-electric-text-muted">
          You closed the Stripe checkout before finishing. Nothing to worry about
          — you can pick a plan again whenever you&apos;re ready.
        </p>
      </div>

      <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
        <Link
          href="/dashboard/billing"
          className="rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg"
        >
          Back to plans
        </Link>
        <Link
          href="/dashboard"
          className="rounded-full border border-electric-border px-5 py-2 text-sm font-semibold text-electric-text"
        >
          Go to dashboard
        </Link>
      </div>
    </main>
  );
}

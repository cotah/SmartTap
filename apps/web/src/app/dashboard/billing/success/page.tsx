import Link from "next/link";

import { getDashboardContext } from "@/lib/dashboard-data";

export default async function BillingSuccessPage() {
  // Auth gate only — we don't trust query params from Stripe to render
  // anything sensitive. The actual activation is driven by the
  // checkout.session.completed webhook, not by this page being visited.
  await getDashboardContext();

  return (
    <main className="mx-auto max-w-xl space-y-6 py-8 text-center">
      <div className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-electric-cyan">
          Payment successful
        </p>
        <h1 className="font-display text-3xl">You&apos;re all set</h1>
        <p className="text-sm text-electric-text-muted">
          Your subscription is being activated. It usually takes just a few seconds
          — you can already start using your new plan.
        </p>
      </div>

      <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
        <Link
          href="/dashboard"
          className="rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg"
        >
          Go to dashboard
        </Link>
        <Link
          href="/dashboard/billing"
          className="rounded-full border border-electric-border px-5 py-2 text-sm font-semibold text-electric-text"
        >
          Back to billing
        </Link>
      </div>

      <p className="pt-4 text-xs text-electric-text-muted">
        Need a receipt? Open the billing portal to download all invoices.
      </p>
    </main>
  );
}

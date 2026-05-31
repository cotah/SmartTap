import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { BillingClient } from "./billing-client";

export default async function BillingPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const subscription = await api.getSubscription();

  return (
    <main className="space-y-8">
      <header>
        <p className="text-sm text-electric-text-muted">
          <Link href="/dashboard" className="underline">
            Dashboard
          </Link>{" "}
          / Billing
        </p>
        <h1 className="font-display text-3xl">Billing</h1>
        <p className="mt-1 text-sm text-electric-text-muted">
          Manage your plan, payment method and invoices.
        </p>
      </header>

      <BillingClient subscription={subscription} />
    </main>
  );
}

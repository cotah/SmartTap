import Link from "next/link";

import { getDashboardContext } from "@/lib/dashboard-data";

import { RedeemForm } from "./redeem-form";

export default async function RedeemPage() {
  await getDashboardContext();

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-brand-black/60">
          <Link href="/dashboard" className="underline">
            Dashboard
          </Link>{" "}
          / Redeem reward
        </p>
        <h1 className="font-display text-3xl">Redeem reward</h1>
        <p className="mt-1 text-sm text-brand-black/60">
          Ask the customer for their 6-digit code, type it in, and confirm.
        </p>
      </header>

      <RedeemForm />
    </main>
  );
}

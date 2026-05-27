import { getDashboardContext } from "@/lib/dashboard-data";

import { RedeemForm } from "./redeem-form";

export default async function RedeemPage() {
  await getDashboardContext();

  return (
    <div className="mx-auto max-w-xl space-y-8">
      <header>
        <h1 className="font-display text-3xl leading-tight text-brand-green sm:text-4xl">
          Redeem reward
        </h1>
        <p className="mt-2 text-sm text-neutral-600">
          Ask the customer for their 6-digit code, type it in, and confirm.
        </p>
      </header>

      <RedeemForm />
    </div>
  );
}

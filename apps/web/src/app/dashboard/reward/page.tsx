import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { RewardForm } from "./reward-form";

export default async function RewardPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { tenant } = await api.getTenant();

  return (
    <main className="space-y-6">
      <header>
        <p className="text-sm text-brand-black/60">
          <Link href="/dashboard" className="underline">
            Dashboard
          </Link>{" "}
          / Reward
        </p>
        <h1 className="font-display text-3xl">Reward</h1>
        <p className="mt-1 text-sm text-brand-black/60">
          Decide how many stamps customers need and what they get.
        </p>
      </header>

      <RewardForm
        initial={{
          stamps_for_reward: tenant.stamps_for_reward,
          reward_description: tenant.reward_description ?? "",
          reward_expires_days: tenant.reward_expires_days,
          stamp_rate_limit_minutes: tenant.stamp_rate_limit_minutes,
        }}
      />
    </main>
  );
}

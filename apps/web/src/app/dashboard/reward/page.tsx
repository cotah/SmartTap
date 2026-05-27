import { getAuthApiClient } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

import { RewardForm } from "./reward-form";

export default async function RewardPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { tenant } = await api.getTenant();

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <header>
        <h1 className="font-display text-3xl leading-tight text-brand-green sm:text-4xl">
          Reward
        </h1>
        <p className="mt-2 text-sm text-neutral-600">
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
    </div>
  );
}

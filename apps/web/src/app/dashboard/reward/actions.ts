"use server";

import { revalidatePath } from "next/cache";

import { ApiError, getAuthApiClient } from "@/lib/api";

export interface RewardFormInput {
  stamps_for_reward: number;
  reward_description: string;
  reward_expires_days: number;
  stamp_rate_limit_minutes: number;
}

export type SaveRewardResult =
  | { ok: true }
  | { ok: false; message: string; fieldErrors?: Record<string, string> };

function inRange(n: number, min: number, max: number): boolean {
  return Number.isFinite(n) && n >= min && n <= max;
}

export async function saveRewardConfigAction(
  input: RewardFormInput,
): Promise<SaveRewardResult> {
  const fieldErrors: Record<string, string> = {};
  if (!inRange(input.stamps_for_reward, 1, 50)) {
    fieldErrors.stamps_for_reward = "Must be between 1 and 50.";
  }
  const desc = (input.reward_description ?? "").trim();
  if (desc.length < 2 || desc.length > 120) {
    fieldErrors.reward_description = "Between 2 and 120 characters.";
  }
  if (!inRange(input.reward_expires_days, 1, 365)) {
    fieldErrors.reward_expires_days = "Between 1 and 365 days.";
  }
  if (!inRange(input.stamp_rate_limit_minutes, 0, 1440)) {
    fieldErrors.stamp_rate_limit_minutes = "Between 0 and 1440 minutes.";
  }
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }

  try {
    const api = getAuthApiClient();
    await api.updateRewardConfig({
      stamps_for_reward: input.stamps_for_reward,
      reward_description: desc,
      reward_expires_days: input.reward_expires_days,
      stamp_rate_limit_minutes: input.stamp_rate_limit_minutes,
    });
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save (API error)." };
    }
    return { ok: false, message: "Could not save. Try again." };
  }

  revalidatePath("/dashboard/reward");
  revalidatePath("/dashboard");
  return { ok: true };
}

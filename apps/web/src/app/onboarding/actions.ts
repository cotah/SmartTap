"use server";

import { redirect } from "next/navigation";

import { ApiError, getAuthApiClient } from "@/lib/api";
import type { OnboardingComplete } from "@/lib/api";

export type OnboardingResult =
  | { ok: true }
  | { ok: false; message: string; fieldErrors?: Record<string, string> };

const HTTP_URL = /^https?:\/\/[^\s]+$/;
const VALID_TYPES = new Set([
  "barbershop",
  "cafe",
  "pet_grooming",
  "salon",
  "tattoo",
  "other",
]);

export async function completeOnboardingAction(
  input: OnboardingComplete,
): Promise<OnboardingResult> {
  const errors: Record<string, string> = {};
  const name = input.business_name.trim();
  if (name.length < 2 || name.length > 80) {
    errors.business_name = "Between 2 and 80 characters.";
  }
  if (!VALID_TYPES.has(input.business_type)) {
    errors.business_type = "Pick the option that fits best.";
  }
  if (input.google_review_url && !HTTP_URL.test(input.google_review_url)) {
    errors.google_review_url = "Must start with http(s):// — or leave blank.";
  }
  const desc = input.reward_description.trim();
  if (desc.length < 2 || desc.length > 120) {
    errors.reward_description = "Between 2 and 120 characters.";
  }
  if (input.stamps_for_reward < 1 || input.stamps_for_reward > 50) {
    errors.stamps_for_reward = "Between 1 and 50.";
  }
  if (input.reward_expires_days < 1 || input.reward_expires_days > 365) {
    errors.reward_expires_days = "Between 1 and 365 days.";
  }
  if (input.stamp_rate_limit_minutes < 0 || input.stamp_rate_limit_minutes > 1440) {
    errors.stamp_rate_limit_minutes = "Between 0 and 1440 minutes.";
  }
  if (Object.keys(errors).length > 0) {
    return { ok: false, message: "Fix the highlighted fields.", fieldErrors: errors };
  }

  try {
    const api = getAuthApiClient();
    await api.completeOnboarding({
      business_name: name,
      business_type: input.business_type,
      google_review_url: input.google_review_url?.trim() || null,
      stamps_for_reward: input.stamps_for_reward,
      reward_description: desc,
      reward_expires_days: input.reward_expires_days,
      stamp_rate_limit_minutes: input.stamp_rate_limit_minutes,
    });
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save." };
    }
    return { ok: false, message: "Network error. Try again." };
  }

  redirect("/dashboard");
}

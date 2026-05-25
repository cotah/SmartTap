"use server";

import { revalidatePath } from "next/cache";

import { ApiError, getAuthApiClient } from "@/lib/api";

export interface RedeemSuccess {
  ok: true;
  reward_id: string;
  description: string;
  customer_name: string | null;
  redeemed_at: string;
}

export interface RedeemFailure {
  ok: false;
  code:
    | "invalid_format"
    | "invalid_code"
    | "already_redeemed"
    | "expired"
    | "network";
  message: string;
}

export type RedeemResult = RedeemSuccess | RedeemFailure;

const SIX_DIGITS = /^\d{6}$/;

export async function redeemByCodeAction(code: string): Promise<RedeemResult> {
  const trimmed = code.trim();
  if (!SIX_DIGITS.test(trimmed)) {
    return {
      ok: false,
      code: "invalid_format",
      message: "Code must be 6 digits.",
    };
  }

  try {
    const api = getAuthApiClient();
    const result = await api.validateRewardByCode(trimmed);
    revalidatePath("/dashboard");
    revalidatePath("/dashboard/customers");
    return {
      ok: true,
      reward_id: result.reward_id,
      description: result.description,
      customer_name: result.customer_name,
      redeemed_at: result.redeemed_at,
    };
  } catch (err) {
    if (err instanceof ApiError) {
      const body = err.body as { error?: { code?: string; message?: string } } | null;
      const apiCode = body?.error?.code;
      const apiMsg = body?.error?.message ?? "Could not validate.";
      if (apiCode === "invalid_code") {
        return {
          ok: false,
          code: "invalid_code",
          message: "No reward matches that code.",
        };
      }
      if (apiCode === "already_redeemed") {
        return {
          ok: false,
          code: "already_redeemed",
          message: "This code has already been used.",
        };
      }
      if (apiCode === "expired") {
        return {
          ok: false,
          code: "expired",
          message: "This reward has expired.",
        };
      }
      return { ok: false, code: "network", message: apiMsg };
    }
    return { ok: false, code: "network", message: "Network error. Try again." };
  }
}

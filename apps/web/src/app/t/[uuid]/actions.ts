"use server";

import { customerIdentifySchema } from "@smarttap/core";

import { ApiError, getApiClient } from "@/lib/api";
import { writeMagicToken } from "@/lib/magic-link";

type OptInResult = { ok: true } | { ok: false; error: string };

export async function optInAction(rawData: unknown): Promise<OptInResult> {
  const parsed = customerIdentifySchema.safeParse(rawData);
  if (!parsed.success) {
    const first = parsed.error.errors[0];
    return { ok: false, error: first?.message ?? "Invalid data" };
  }

  try {
    const api = getApiClient();
    // Drop empty-string email before hitting the backend — Pydantic EmailStr
    // rejects "" but the form sends it for an untouched optional input.
    const payload = { ...parsed.data };
    if (!payload.email) {
      delete payload.email;
    }
    const result = await api.identifyCustomer(payload);
    await writeMagicToken(result.magic_link_token);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      const body = err.body as { error?: { message?: string } } | null;
      return { ok: false, error: body?.error?.message ?? `Request failed (${err.status})` };
    }
    return { ok: false, error: "Unexpected error. Try again." };
  }
}

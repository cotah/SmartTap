"use server";

import { customerIdentifySchema } from "@smarttap/core";

import { ApiError, getApiClient } from "@/lib/api";
import { writeMagicToken } from "@/lib/magic-link";

type OptInResult = { ok: true } | { ok: false; error: string };
type ActionResult = { ok: true } | { ok: false; error: string };

const PHONE_RE = /^\+353[1-9]\d{6,9}$/;
const CODE_RE = /^\d{4}$/;

/**
 * Sprint 5.6 — "Already a member?" step 1. Always resolves ok when the request
 * reaches the backend (the backend is anti-enumeration: it only texts a code
 * if the phone is a real customer, but never says so).
 */
export async function requestCodeAction(
  tenantId: string,
  phone: string,
): Promise<ActionResult> {
  if (!PHONE_RE.test(phone)) {
    return { ok: false, error: "Enter a valid Irish mobile number." };
  }
  try {
    const api = getApiClient();
    await api.requestIdentifyCode({ tenant_id: tenantId, phone });
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      const body = err.body as { error?: { message?: string } } | null;
      return {
        ok: false,
        error: body?.error?.message ?? `Request failed (${err.status})`,
      };
    }
    return { ok: false, error: "Unexpected error. Try again." };
  }
}

/**
 * Step 2 — verify the code. On success the backend returns the customer's
 * magic_link_token; we set the same `smarttap_magic` cookie the opt-in flow
 * uses, so the caller's router.refresh() re-taps and restores their stamps.
 */
export async function verifyCodeAction(
  tenantId: string,
  phone: string,
  code: string,
): Promise<ActionResult> {
  if (!CODE_RE.test(code)) {
    return { ok: false, error: "Enter the 4-digit code." };
  }
  try {
    const api = getApiClient();
    const result = await api.verifyIdentifyCode({
      tenant_id: tenantId,
      phone,
      code,
    });
    await writeMagicToken(result.magic_link_token);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, error: messageForVerifyError(err) };
    }
    return { ok: false, error: "Unexpected error. Try again." };
  }
}

function messageForVerifyError(err: ApiError): string {
  const code = (err.body as { error?: { code?: string } } | null)?.error?.code;
  switch (code) {
    case "invalid_code":
      return "That code isn't right. Check it and try again.";
    case "expired":
      return "That code expired. Request a new one.";
    case "rate_limited":
      return "Too many tries. Request a fresh code in a moment.";
    default:
      return `Couldn't verify (${err.status}).`;
  }
}

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

"use server";

import { ApiError, getAuthApiClient } from "@/lib/api";
import type { BillingPlanId } from "@/lib/api";
import { publicEnv } from "@/lib/env";

export type StripeRedirectResult =
  | { ok: true; url: string }
  | { ok: false; message: string };

const SITE_URL = publicEnv.NEXT_PUBLIC_SITE_URL.replace(/\/$/, "");

/**
 * Create a Stripe Checkout session for a given plan.
 * Caller is expected to navigate to `url` on success.
 *
 * Note: we don't redirect server-side because Stripe's URL is on a different
 * origin and the result might be shown inline (e.g. opening in a new tab in a
 * future iteration). Returning the URL keeps that flexibility.
 */
export async function startCheckoutAction(
  plan: BillingPlanId,
): Promise<StripeRedirectResult> {
  try {
    const api = getAuthApiClient();
    const { url } = await api.createCheckoutSession({
      plan,
      success_url: `${SITE_URL}/dashboard/billing/success`,
      cancel_url: `${SITE_URL}/dashboard/billing/canceled`,
    });
    return { ok: true, url };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not start checkout." };
    }
    return { ok: false, message: "Could not start checkout. Try again." };
  }
}

/**
 * Open the Stripe Customer Portal — used for plan changes, payment method,
 * invoices, cancellation. Requires the tenant to already have a Stripe
 * customer attached (any tenant that completed at least one checkout).
 */
export async function openPortalAction(): Promise<StripeRedirectResult> {
  try {
    const api = getAuthApiClient();
    const { url } = await api.createPortalSession({
      return_url: `${SITE_URL}/dashboard/billing`,
    });
    return { ok: true, url };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not open billing portal." };
    }
    return { ok: false, message: "Could not open billing portal. Try again." };
  }
}

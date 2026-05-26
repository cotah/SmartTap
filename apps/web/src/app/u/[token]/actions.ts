"use server";

import { ApiError, getApiClient } from "@/lib/api";

export type OptOutResult =
  | { ok: true }
  | { ok: false; error: string; status?: number };

export async function optOutAction(token: string): Promise<OptOutResult> {
  // Trim and bound — the URL segment already constrains length on the
  // backend (8-128), but a friendlier client-side guard avoids a confusing
  // 404 if someone hand-types a bad token.
  const cleaned = token.trim();
  if (cleaned.length < 8) {
    return { ok: false, error: "This unsubscribe link looks incomplete." };
  }

  try {
    const api = getApiClient();
    await api.optOutCustomer(cleaned);
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      // 404 = unknown token. Treat as "already opted out OR bad link" without
      // being specific — the backend deliberately avoids telling us which,
      // and we don't want to teach users to retry with tweaked tokens.
      if (err.status === 404) {
        return {
          ok: false,
          error: "We couldn't find that subscription. It may have already been removed.",
          status: 404,
        };
      }
      return { ok: false, error: `Request failed (${err.status}).`, status: err.status };
    }
    return { ok: false, error: "Unexpected error. Try again in a moment." };
  }
}

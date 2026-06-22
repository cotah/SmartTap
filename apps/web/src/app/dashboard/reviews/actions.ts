"use server";

import { revalidatePath } from "next/cache";

import { ApiError, getAuthApiClient } from "@/lib/api";
import type { Review } from "@/lib/api";

export type ReviewActionResult =
  | { ok: true; review: Review }
  | { ok: false; message: string };

export type ConnectResult = { ok: true; url: string } | { ok: false; message: string };

/**
 * Save the owner's edited reply, then publish it to Google. The backend's
 * publish endpoint falls back to the AI draft if reply_text is empty, but we
 * persist the edited text first so what the owner sees is what gets posted.
 */
export async function publishReviewAction(
  id: string,
  replyText: string,
): Promise<ReviewActionResult> {
  const text = (replyText ?? "").trim();
  if (text.length === 0) {
    return { ok: false, message: "Write a reply before publishing." };
  }
  try {
    const api = getAuthApiClient();
    await api.updateReviewReply(id, text);
    const review = await api.publishReview(id);
    revalidatePath("/dashboard/reviews");
    return { ok: true, review };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not publish reply." };
    }
    return { ok: false, message: "Could not publish reply. Try again." };
  }
}

export async function saveReplyAction(
  id: string,
  replyText: string,
): Promise<ReviewActionResult> {
  const text = (replyText ?? "").trim();
  if (text.length === 0) {
    return { ok: false, message: "Reply can't be empty." };
  }
  try {
    const api = getAuthApiClient();
    const review = await api.updateReviewReply(id, text);
    revalidatePath("/dashboard/reviews");
    return { ok: true, review };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save reply." };
    }
    return { ok: false, message: "Could not save reply. Try again." };
  }
}

export async function dismissReviewAction(id: string): Promise<ReviewActionResult> {
  try {
    const api = getAuthApiClient();
    const review = await api.dismissReview(id);
    revalidatePath("/dashboard/reviews");
    return { ok: true, review };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not dismiss review." };
    }
    return { ok: false, message: "Could not dismiss review. Try again." };
  }
}

/** Returns the Google consent URL so the client can navigate the browser to it. */
export async function connectGoogleAction(): Promise<ConnectResult> {
  try {
    const api = getAuthApiClient();
    const { url } = await api.getGoogleConnectUrl();
    return { ok: true, url };
  } catch (err) {
    if (err instanceof ApiError) {
      const message =
        err.status === 503
          ? "Google integration isn't configured yet."
          : err.message || "Could not start Google connection.";
      return { ok: false, message };
    }
    return { ok: false, message: "Could not start Google connection. Try again." };
  }
}

export type DisconnectResult = { ok: true } | { ok: false; message: string };

/** Remove the tenant's Google connection, then refresh the reviews page. */
export async function disconnectGoogleAction(): Promise<DisconnectResult> {
  try {
    const api = getAuthApiClient();
    await api.disconnectGoogle();
    revalidatePath("/dashboard/reviews");
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not disconnect Google." };
    }
    return { ok: false, message: "Could not disconnect Google. Try again." };
  }
}

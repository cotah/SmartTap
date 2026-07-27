"use server";

import { revalidatePath } from "next/cache";

import { ApiError, getAuthApiClient } from "@/lib/api";

export interface SettingsFormInput {
  name: string;
  primary_color: string;
  accent_color: string;
  logo_url: string;
  google_review_url: string;
  google_business_url: string;
  google_place_id: string;
  opening_hours: string;
  menu_info: string;
  brand_voice: string;
}

export type SaveSettingsResult =
  | { ok: true }
  | { ok: false; message: string; fieldErrors?: Record<string, string> };

const HEX = /^#[0-9A-Fa-f]{6}$/;

function isValidUrl(value: string): boolean {
  try {
    const u = new URL(value);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

export async function saveSettingsAction(
  input: SettingsFormInput,
): Promise<SaveSettingsResult> {
  const fieldErrors: Record<string, string> = {};

  const name = input.name.trim();
  if (name.length < 2 || name.length > 80) {
    fieldErrors.name = "Between 2 and 80 characters.";
  }
  if (!HEX.test(input.primary_color)) {
    fieldErrors.primary_color = "Must be #RRGGBB hex.";
  }
  if (!HEX.test(input.accent_color)) {
    fieldErrors.accent_color = "Must be #RRGGBB hex.";
  }
  for (const k of ["logo_url", "google_review_url", "google_business_url"] as const) {
    const v = input[k].trim();
    if (v && !isValidUrl(v)) {
      fieldErrors[k] = "Must be a full URL starting with http(s)://";
    }
  }
  // AI assistant context — mirror the backend max lengths so the owner gets
  // a friendly error instead of a raw 422.
  const AI_LIMITS = { opening_hours: 1000, menu_info: 4000, brand_voice: 1000 } as const;
  for (const k of ["opening_hours", "menu_info", "brand_voice"] as const) {
    if (input[k].trim().length > AI_LIMITS[k]) {
      fieldErrors[k] = `Maximum ${AI_LIMITS[k]} characters.`;
    }
  }
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }

  try {
    const api = getAuthApiClient();
    await api.updateTenantSettings({
      name,
      primary_color: input.primary_color,
      accent_color: input.accent_color,
      // Empty string clears the field server-side; otherwise we send the trimmed value.
      logo_url: input.logo_url.trim(),
      google_review_url: input.google_review_url.trim(),
      google_business_url: input.google_business_url.trim(),
      google_place_id: input.google_place_id.trim(),
      opening_hours: input.opening_hours.trim(),
      menu_info: input.menu_info.trim(),
      brand_voice: input.brand_voice.trim(),
    });
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save (API error)." };
    }
    return { ok: false, message: "Could not save. Try again." };
  }

  revalidatePath("/dashboard/settings");
  revalidatePath("/dashboard");
  return { ok: true };
}

export type ConnectResult = { ok: true; url: string } | { ok: false; message: string };
export type DisconnectResult = { ok: true } | { ok: false; message: string };

/** Returns the Meta consent URL so the client can navigate the browser to it. */
export async function connectInstagramAction(): Promise<ConnectResult> {
  try {
    const api = getAuthApiClient();
    const { url } = await api.getInstagramConnectUrl();
    return { ok: true, url };
  } catch (err) {
    if (err instanceof ApiError) {
      const message =
        err.status === 503
          ? "Instagram integration isn't configured yet."
          : err.message || "Could not start Instagram connection.";
      return { ok: false, message };
    }
    return { ok: false, message: "Could not start Instagram connection. Try again." };
  }
}

export type SelectPageResult = { ok: true } | { ok: false; message: string };

/**
 * Page Picker — finalise the pending connection by choosing one Facebook
 * Page. The backend re-resolves the page via the stored user token, so we
 * only ever send the page id (never tokens).
 */
export async function selectInstagramPageAction(
  facebookPageId: string,
): Promise<SelectPageResult> {
  try {
    const api = getAuthApiClient();
    await api.selectInstagramPage(facebookPageId);
    revalidatePath("/dashboard/settings");
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      const message =
        err.status === 404
          ? "This selection expired. Please connect Instagram again."
          : err.message || "Could not connect the selected page.";
      return { ok: false, message };
    }
    return { ok: false, message: "Could not connect the selected page. Try again." };
  }
}

/** Remove the tenant's Instagram connection, then refresh the settings page. */
export async function disconnectInstagramAction(): Promise<DisconnectResult> {
  try {
    const api = getAuthApiClient();
    await api.disconnectInstagram();
    revalidatePath("/dashboard/settings");
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not disconnect Instagram." };
    }
    return { ok: false, message: "Could not disconnect Instagram. Try again." };
  }
}

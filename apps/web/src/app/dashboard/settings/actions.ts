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

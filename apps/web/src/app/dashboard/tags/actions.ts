"use server";

import { revalidatePath } from "next/cache";

import { ApiError, getAuthApiClient } from "@/lib/api";
import type { NfcTagColor, NfcTagFormat } from "@/lib/api";

export interface TagFormInput {
  format: NfcTagFormat;
  color: NfcTagColor;
  location_name: string;
}

export type TagActionResult =
  | { ok: true; tagId: string }
  | { ok: false; message: string; fieldErrors?: Record<string, string> };

function validateInput(input: TagFormInput): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!input.format) errors.format = "Pick a format.";
  if (!input.color) errors.color = "Pick a colour.";
  if (input.location_name.length > 80) {
    errors.location_name = "Keep the name under 80 characters.";
  }
  return errors;
}

export async function createTagAction(
  input: TagFormInput,
): Promise<TagActionResult> {
  const fieldErrors = validateInput(input);
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }
  try {
    const api = getAuthApiClient();
    const tag = await api.createTag({
      format: input.format,
      color: input.color,
      // Empty string → null so the backend stores NULL and the fallback
      // label ("<format> · <color>") kicks in on the dashboard.
      location_name: input.location_name.trim() || null,
    });
    revalidatePath("/dashboard/tags");
    return { ok: true, tagId: tag.id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save tag." };
    }
    return { ok: false, message: "Could not save tag. Try again." };
  }
}

export async function updateTagAction(
  id: string,
  input: TagFormInput,
): Promise<TagActionResult> {
  const fieldErrors = validateInput(input);
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }
  try {
    const api = getAuthApiClient();
    await api.updateTag(id, {
      format: input.format,
      color: input.color,
      location_name: input.location_name.trim() || null,
    });
    revalidatePath("/dashboard/tags");
    revalidatePath(`/dashboard/tags/${id}`);
    return { ok: true, tagId: id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save tag." };
    }
    return { ok: false, message: "Could not save tag. Try again." };
  }
}

export async function toggleTagActiveAction(
  id: string,
  is_active: boolean,
): Promise<TagActionResult> {
  try {
    const api = getAuthApiClient();
    await api.updateTag(id, { is_active });
    revalidatePath("/dashboard/tags");
    revalidatePath(`/dashboard/tags/${id}`);
    return { ok: true, tagId: id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not change status." };
    }
    return { ok: false, message: "Could not change status. Try again." };
  }
}

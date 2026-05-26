"use server";

import { revalidatePath } from "next/cache";

import { ApiError, getAuthApiClient } from "@/lib/api";
import type { SegmentCriteria, SegmentPreview } from "@/lib/api";

export interface SegmentFormInput {
  name: string;
  criteria: SegmentCriteria;
}

export type SegmentActionResult =
  | { ok: true; segmentId: string }
  | { ok: false; message: string; fieldErrors?: Record<string, string> };

export type SegmentDeleteResult =
  | { ok: true }
  | { ok: false; message: string };

export type SegmentPreviewResult =
  | { ok: true; preview: SegmentPreview }
  | { ok: false; message: string };

function validateInput(input: SegmentFormInput): Record<string, string> {
  const errors: Record<string, string> = {};
  const name = (input.name ?? "").trim();
  if (name.length < 2 || name.length > 80) {
    errors.name = "Name must be 2–80 characters.";
  }
  const c = input.criteria;
  // Range coherence — same checks the backend will run, mirrored here so the
  // form can highlight the offending field rather than show a generic error.
  if (
    typeof c.visits_min === "number" &&
    typeof c.visits_max === "number" &&
    c.visits_min > c.visits_max
  ) {
    errors.visits_max = "Max visits must be greater than or equal to min.";
  }
  if (
    typeof c.stamps_min === "number" &&
    typeof c.stamps_max === "number" &&
    c.stamps_min > c.stamps_max
  ) {
    errors.stamps_max = "Max stamps must be greater than or equal to min.";
  }
  return errors;
}

export async function createSegmentAction(
  input: SegmentFormInput,
): Promise<SegmentActionResult> {
  const fieldErrors = validateInput(input);
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }
  try {
    const api = getAuthApiClient();
    const seg = await api.createSegment({
      name: input.name.trim(),
      criteria: input.criteria,
    });
    revalidatePath("/dashboard/segments");
    return { ok: true, segmentId: seg.id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save segment." };
    }
    return { ok: false, message: "Could not save segment. Try again." };
  }
}

export async function updateSegmentAction(
  id: string,
  input: SegmentFormInput,
): Promise<SegmentActionResult> {
  const fieldErrors = validateInput(input);
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }
  try {
    const api = getAuthApiClient();
    await api.updateSegment(id, {
      name: input.name.trim(),
      criteria: input.criteria,
    });
    revalidatePath("/dashboard/segments");
    revalidatePath(`/dashboard/segments/${id}`);
    return { ok: true, segmentId: id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not save segment." };
    }
    return { ok: false, message: "Could not save segment. Try again." };
  }
}

export async function deleteSegmentAction(id: string): Promise<SegmentDeleteResult> {
  try {
    const api = getAuthApiClient();
    await api.deleteSegment(id);
    revalidatePath("/dashboard/segments");
    return { ok: true };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not delete segment." };
    }
    return { ok: false, message: "Could not delete segment. Try again." };
  }
}

/**
 * Preview an unsaved criteria payload. Backed by POST /v1/segments/preview
 * so the merchant can iterate on the criteria before committing — no DB row
 * is created here.
 */
export async function previewUnsavedSegmentAction(
  input: SegmentFormInput,
): Promise<SegmentPreviewResult> {
  try {
    const api = getAuthApiClient();
    const preview = await api.previewUnsavedSegment(
      { name: input.name || "Preview", criteria: input.criteria },
      20,
    );
    return { ok: true, preview };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not preview." };
    }
    return { ok: false, message: "Could not preview. Try again." };
  }
}

/**
 * Preview a saved segment by id. Use this on the edit page so the merchant
 * sees what the *currently saved* criteria match, independent of unsaved
 * edits in the form.
 */
export async function previewSavedSegmentAction(
  id: string,
): Promise<SegmentPreviewResult> {
  try {
    const api = getAuthApiClient();
    const preview = await api.previewSegment(id, 20);
    return { ok: true, preview };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not preview." };
    }
    return { ok: false, message: "Could not preview. Try again." };
  }
}

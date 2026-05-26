"use server";

import { revalidatePath } from "next/cache";

import { ApiError, getAuthApiClient } from "@/lib/api";
import type { CampaignStatus } from "@/lib/api";

export interface CampaignFormInput {
  name: string;
  multiplier: number;
  starts_at: string; // ISO from <input type="datetime-local"> after toISOString
  ends_at: string;
  status: "draft" | "active";
}

export type CampaignActionResult =
  | { ok: true; campaignId: string }
  | { ok: false; message: string; fieldErrors?: Record<string, string> };

function validateInput(input: CampaignFormInput): Record<string, string> {
  const errors: Record<string, string> = {};
  const name = (input.name ?? "").trim();
  if (name.length < 2 || name.length > 80) {
    errors.name = "Name must be 2–80 characters.";
  }
  if (
    !Number.isFinite(input.multiplier) ||
    input.multiplier < 2 ||
    input.multiplier > 5
  ) {
    errors.multiplier = "Multiplier must be between 2 and 5.";
  }
  const starts = Date.parse(input.starts_at);
  const ends = Date.parse(input.ends_at);
  if (Number.isNaN(starts)) errors.starts_at = "Pick a start date and time.";
  if (Number.isNaN(ends)) errors.ends_at = "Pick an end date and time.";
  if (!Number.isNaN(starts) && !Number.isNaN(ends) && ends <= starts) {
    errors.ends_at = "End must be after start.";
  }
  return errors;
}

export async function createCampaignAction(
  input: CampaignFormInput,
): Promise<CampaignActionResult> {
  const fieldErrors = validateInput(input);
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }

  try {
    const api = getAuthApiClient();
    const campaign = await api.createCampaign({
      name: input.name.trim(),
      multiplier: input.multiplier,
      starts_at: input.starts_at,
      ends_at: input.ends_at,
      status: input.status,
    });
    revalidatePath("/dashboard/campaigns");
    return { ok: true, campaignId: campaign.id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not create campaign." };
    }
    return { ok: false, message: "Could not create campaign. Try again." };
  }
}

export async function updateCampaignAction(
  id: string,
  input: CampaignFormInput,
): Promise<CampaignActionResult> {
  const fieldErrors = validateInput(input);
  if (Object.keys(fieldErrors).length > 0) {
    return { ok: false, message: "Please fix the highlighted fields.", fieldErrors };
  }

  try {
    const api = getAuthApiClient();
    await api.updateCampaign(id, {
      name: input.name.trim(),
      multiplier: input.multiplier,
      starts_at: input.starts_at,
      ends_at: input.ends_at,
    });
    revalidatePath("/dashboard/campaigns");
    revalidatePath(`/dashboard/campaigns/${id}`);
    return { ok: true, campaignId: id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not update campaign." };
    }
    return { ok: false, message: "Could not update campaign. Try again." };
  }
}

export async function changeCampaignStatusAction(
  id: string,
  status: CampaignStatus,
): Promise<CampaignActionResult> {
  try {
    const api = getAuthApiClient();
    await api.changeCampaignStatus(id, status);
    revalidatePath("/dashboard/campaigns");
    revalidatePath(`/dashboard/campaigns/${id}`);
    return { ok: true, campaignId: id };
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not change status." };
    }
    return { ok: false, message: "Could not change status. Try again." };
  }
}

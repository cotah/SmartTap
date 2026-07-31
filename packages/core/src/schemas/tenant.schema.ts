import { z } from "zod";

export const businessTypeSchema = z.enum([
  "barbershop",
  "cafe",
  "pet_grooming",
  "salon",
  "tattoo",
  "restaurant",
  "other",
]);

export const tenantPlanSchema = z.enum(["trial", "review", "loyalty", "pro", "network"]);

export const tenantSettingsUpdateSchema = z.object({
  name: z.string().min(2).max(80).optional(),
  logo_url: z.string().url().nullable().optional(),
  primary_color: z
    .string()
    .regex(/^#[0-9A-Fa-f]{6}$/, "Must be a #RRGGBB hex color")
    .optional(),
  accent_color: z
    .string()
    .regex(/^#[0-9A-Fa-f]{6}$/)
    .optional(),
  google_place_id: z.string().nullable().optional(),
  google_review_url: z.string().url().nullable().optional(),
  google_business_url: z.string().url().nullable().optional(),
  // AI assistant context (review reply drafting). Empty string clears the
  // field server-side; null/undefined leaves it unchanged.
  opening_hours: z.string().max(1000).nullable().optional(),
  menu_info: z.string().max(4000).nullable().optional(),
  brand_voice: z.string().max(1000).nullable().optional(),
});

export const rewardConfigSchema = z.object({
  stamps_for_reward: z.number().int().min(1).max(50),
  reward_description: z.string().min(2).max(120),
  reward_expires_days: z.number().int().min(1).max(365),
  stamp_rate_limit_minutes: z.number().int().min(0).max(1440),
});

export type TenantSettingsUpdate = z.infer<typeof tenantSettingsUpdateSchema>;
export type RewardConfig = z.infer<typeof rewardConfigSchema>;

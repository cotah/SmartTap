export type TenantPlan = "trial" | "review" | "loyalty" | "pro" | "network";

export type BusinessType =
  | "barbershop"
  | "cafe"
  | "pet_grooming"
  | "salon"
  | "tattoo"
  | "other";

export interface Tenant {
  id: string;
  slug: string;
  name: string;
  business_type: BusinessType;
  logo_url: string | null;
  primary_color: string;
  accent_color: string;
  google_place_id: string | null;
  google_review_url: string | null;
  google_business_url: string | null;
  stamps_for_reward: number;
  reward_description: string | null;
  reward_expires_days: number;
  stamp_rate_limit_minutes: number;
  plan: TenantPlan;
  is_founding_member: boolean;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  trial_ends_at: string | null;
  is_active: boolean;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

import "server-only";

import { cookies } from "next/headers";

import { ApiError, createApiClient, type ApiClient } from "@smarttap/api";

import { getAccessToken } from "./auth";
import { publicEnv } from "./env";

/** Cookie holding the active tenant id for multi-tenant users. */
export const ACTIVE_TENANT_COOKIE = "st-active-tenant";

export function getApiClient(): ApiClient {
  return createApiClient({ baseUrl: publicEnv.NEXT_PUBLIC_API_URL });
}

export function getAuthApiClient(tenantIdOverride?: string): ApiClient {
  return createApiClient({
    baseUrl: publicEnv.NEXT_PUBLIC_API_URL,
    getToken: getAccessToken,
    // Explicit override (e.g. per-restaurant actions) wins over the cookie
    // set by the tenant switcher. Backend validates membership either way.
    getTenantId: async () =>
      tenantIdOverride ?? (await cookies()).get(ACTIVE_TENANT_COOKIE)?.value ?? null,
  });
}

export { ApiError };
export type {
  TapResponse,
  TenantPublic,
  TenantSummary,
  TenantSelf,
  CustomerSnapshot,
  RewardStateSnapshot,
  RewardAvailable,
  IdentifyResponse,
  ValidateRewardResponse,
  DashboardOverview,
  TapPoint,
  TapsTimeseries,
  MeResponse,
  BootstrapResponse,
  CustomerListFilter,
  CustomerListSort,
  CustomerListItem,
  CustomerListResponse,
  CustomerListParams,
  CustomerStats,
  OnboardingComplete,
  BillingPlanId,
  CheckoutSessionInput,
  PortalSessionInput,
  SubscriptionInfo,
  TrialStatus,
  ActiveCampaign,
  Campaign,
  CampaignType,
  CampaignStatus,
  CampaignCreateInput,
  CampaignUpdateInput,
  Segment,
  SegmentCriteria,
  SegmentCreateInput,
  SegmentUpdateInput,
  SegmentCustomerPreview,
  SegmentPreview,
  NfcTag,
  NfcTagFormat,
  NfcTagColor,
  NfcTagCreateInput,
  NfcTagUpdateInput,
  Review,
  ReviewStatus,
  RatingBucket,
  ReviewStats,
  GoogleStatus,
  InstagramStatus,
  InstagramPage,
} from "@smarttap/api";

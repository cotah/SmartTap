import "server-only";

import { ApiError, createApiClient, type ApiClient } from "@smarttap/api";

import { getAccessToken } from "./auth";
import { publicEnv } from "./env";

export function getApiClient(): ApiClient {
  return createApiClient({ baseUrl: publicEnv.NEXT_PUBLIC_API_URL });
}

export function getAuthApiClient(): ApiClient {
  return createApiClient({
    baseUrl: publicEnv.NEXT_PUBLIC_API_URL,
    getToken: getAccessToken,
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
  MeResponse,
  BootstrapResponse,
  CustomerListFilter,
  CustomerListSort,
  CustomerListItem,
  CustomerListResponse,
  CustomerListParams,
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
} from "@smarttap/api";

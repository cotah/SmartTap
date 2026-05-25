import type {
  Tenant,
  TenantPlan,
  BusinessType,
  Customer,
  CustomerIdentify,
  TapEvent,
  RewardConfig,
  TenantSettingsUpdate,
} from "@smarttap/core";

export interface ApiClientOptions {
  baseUrl: string;
  getToken?: () => Promise<string | null>;
  fetchImpl?: typeof fetch;
}

export interface BusinessErrorBody {
  error: { code: string; message: string; detail: Record<string, string> };
}

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, message: string, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export type TenantPublic = Pick<
  Tenant,
  | "id"
  | "slug"
  | "name"
  | "logo_url"
  | "primary_color"
  | "accent_color"
  | "reward_description"
  | "google_review_url"
>;

export type CustomerSnapshot = Pick<Customer, "id" | "name" | "current_stamps">;

export interface RewardStateSnapshot {
  current_stamps: number;
  stamps_for_reward: number;
  stamps_remaining: number;
  reward_ready: boolean;
  progress_percent: number;
}

export interface RewardAvailable {
  id: string;
  validation_code: string;
  description: string;
  expires_at: string;
}

export interface TapResponse {
  tenant: TenantPublic;
  customer: CustomerSnapshot | null;
  tap_id: string;
  stamp_awarded: boolean;
  stamps_current: number;
  reward_state: RewardStateSnapshot;
  reward_available: RewardAvailable | null;
}

export interface IdentifyResponse {
  customer_id: string;
  magic_link_token: string;
  stamps_current: number;
}

export interface ValidateRewardResponse {
  reward_id: string;
  redeemed_at: string;
  description: string;
  customer_id: string;
  customer_name: string | null;
}

export interface DashboardOverview {
  customers_total: number;
  taps_week: number;
  reviews_month: number;
  customers_at_risk: number;
  active_stamps_total: number;
}

export type CustomerListFilter = "all" | "active" | "at_risk" | "has_reward";
export type CustomerListSort = "recent" | "visits" | "stamps";

export interface CustomerListItem {
  id: string;
  name: string | null;
  phone: string | null;
  current_stamps: number;
  total_visits: number;
  last_visit_at: string | null;
  created_at: string;
  has_reward_ready: boolean;
}

export interface CustomerListResponse {
  items: CustomerListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface CustomerListParams {
  search?: string;
  filter?: CustomerListFilter;
  sort?: CustomerListSort;
  page?: number;
  limit?: number;
}

export interface TenantSummary {
  id: string;
  slug: string;
  name: string;
  business_type: BusinessType;
  plan: TenantPlan;
  is_active: boolean;
  trial_ends_at: string | null;
  onboarding_complete: boolean;
}

export interface OnboardingComplete {
  business_name: string;
  business_type: BusinessType;
  google_review_url: string | null;
  stamps_for_reward: number;
  reward_description: string;
  reward_expires_days: number;
  stamp_rate_limit_minutes: number;
}

/**
 * Tenant fields returned to the dashboard owner.
 * Excludes billing internals (stripe ids) intentionally.
 */
export interface TenantSelf {
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
  is_active: boolean;
  is_founding_member: boolean;
  trial_ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MeResponse {
  user_id: string;
  email: string | null;
  tenant: TenantSummary | null;
}

export interface BootstrapInput {
  business_name?: string | null;
}

export interface BootstrapResponse {
  tenant: TenantSummary;
  is_new: boolean;
}

export interface ApiClient {
  tap: (tagUuid: string, body: TapEvent) => Promise<TapResponse>;
  identifyCustomer: (body: CustomerIdentify) => Promise<IdentifyResponse>;
  getMe: () => Promise<MeResponse>;
  bootstrapMe: (body: BootstrapInput) => Promise<BootstrapResponse>;
  getOverview: () => Promise<DashboardOverview>;
  listCustomers: (params?: CustomerListParams) => Promise<CustomerListResponse>;
  getTenant: () => Promise<{ tenant: TenantSelf }>;
  updateTenantSettings: (body: TenantSettingsUpdate) => Promise<{ tenant: TenantSelf }>;
  updateRewardConfig: (body: RewardConfig) => Promise<{ tenant: TenantSelf }>;
  validateReward: (rewardId: string, code: string) => Promise<ValidateRewardResponse>;
  validateRewardByCode: (code: string) => Promise<ValidateRewardResponse>;
  exportCustomersCsv: (params?: Omit<CustomerListParams, "page" | "limit">) => Promise<string>;
  completeOnboarding: (body: OnboardingComplete) => Promise<TenantSummary>;
}

export function createApiClient(opts: ApiClientOptions): ApiClient {
  const fetchImpl = opts.fetchImpl ?? fetch;
  const baseUrl = opts.baseUrl.replace(/\/$/, "");

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string> | undefined),
    };
    if (opts.getToken) {
      const token = await opts.getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetchImpl(`${baseUrl}${path}`, { ...init, headers });
    const text = await res.text();
    const body = text ? (JSON.parse(text) as unknown) : null;
    if (!res.ok) {
      throw new ApiError(res.status, res.statusText, body);
    }
    return body as T;
  }

  async function requestText(path: string, init: RequestInit = {}): Promise<string> {
    const headers: Record<string, string> = {
      ...(init.headers as Record<string, string> | undefined),
    };
    if (opts.getToken) {
      const token = await opts.getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetchImpl(`${baseUrl}${path}`, { ...init, headers });
    const text = await res.text();
    if (!res.ok) {
      throw new ApiError(res.status, res.statusText, text);
    }
    return text;
  }

  return {
    tap: (tagUuid, body) =>
      request<TapResponse>(`/v1/taps/${tagUuid}`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    identifyCustomer: (body) =>
      request<IdentifyResponse>(`/v1/customers/identify`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    getMe: () => request<MeResponse>(`/v1/me`),
    bootstrapMe: (body) =>
      request<BootstrapResponse>(`/v1/me/bootstrap`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    getOverview: () => request<DashboardOverview>(`/v1/dashboard/overview`),
    listCustomers: (params) => {
      const qs = new URLSearchParams();
      if (params?.search) qs.set("search", params.search);
      if (params?.filter) qs.set("filter", params.filter);
      if (params?.sort) qs.set("sort", params.sort);
      if (params?.page) qs.set("page", String(params.page));
      if (params?.limit) qs.set("limit", String(params.limit));
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      return request<CustomerListResponse>(`/v1/customers${suffix}`);
    },
    getTenant: () => request<{ tenant: TenantSelf }>(`/v1/tenant`),
    updateTenantSettings: (body) =>
      request<{ tenant: TenantSelf }>(`/v1/tenant/settings`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    updateRewardConfig: (body) =>
      request<{ tenant: TenantSelf }>(`/v1/tenant/reward-config`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    validateReward: (rewardId, code) =>
      request<ValidateRewardResponse>(`/v1/rewards/${rewardId}/validate`, {
        method: "POST",
        body: JSON.stringify({ validation_code: code }),
      }),
    validateRewardByCode: (code) =>
      request<ValidateRewardResponse>(`/v1/rewards/validate`, {
        method: "POST",
        body: JSON.stringify({ validation_code: code }),
      }),
    exportCustomersCsv: (params) => {
      const qs = new URLSearchParams();
      if (params?.search) qs.set("search", params.search);
      if (params?.filter) qs.set("filter", params.filter);
      if (params?.sort) qs.set("sort", params.sort);
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      return requestText(`/v1/customers/export.csv${suffix}`);
    },
    completeOnboarding: (body) =>
      request<TenantSummary>(`/v1/onboarding/complete`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
  };
}

import type {
  Tenant,
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
}

export interface DashboardOverview {
  customers_total: number;
  taps_week: number;
  reviews_month: number;
  customers_at_risk: number;
  active_stamps_total: number;
}

export interface ApiClient {
  tap: (tagUuid: string, body: TapEvent) => Promise<TapResponse>;
  identifyCustomer: (body: CustomerIdentify) => Promise<IdentifyResponse>;
  getOverview: () => Promise<DashboardOverview>;
  updateTenantSettings: (body: TenantSettingsUpdate) => Promise<{ tenant: Tenant }>;
  updateRewardConfig: (body: RewardConfig) => Promise<{ tenant: Tenant }>;
  validateReward: (rewardId: string, code: string) => Promise<ValidateRewardResponse>;
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
    getOverview: () => request<DashboardOverview>(`/v1/dashboard/overview`),
    updateTenantSettings: (body) =>
      request<{ tenant: Tenant }>(`/v1/tenant/settings`, {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    updateRewardConfig: (body) =>
      request<{ tenant: Tenant }>(`/v1/tenant/reward-config`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    validateReward: (rewardId, code) =>
      request<ValidateRewardResponse>(`/v1/rewards/${rewardId}/validate`, {
        method: "POST",
        body: JSON.stringify({ validation_code: code }),
      }),
  };
}

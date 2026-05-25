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

export interface TapResponse {
  tenant: Pick<Tenant, "id" | "slug" | "name" | "logo_url" | "primary_color" | "accent_color">;
  customer: Pick<Customer, "id" | "name" | "current_stamps"> | null;
  stamps_current: number;
  reward_available: { id: string; validation_code: string; description: string } | null;
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
  identifyCustomer: (body: CustomerIdentify) => Promise<{
    customer_id: string;
    magic_link_token: string;
    stamps_current: number;
  }>;
  getOverview: () => Promise<DashboardOverview>;
  updateTenantSettings: (body: TenantSettingsUpdate) => Promise<{ tenant: Tenant }>;
  updateRewardConfig: (body: RewardConfig) => Promise<{ tenant: Tenant }>;
  validateReward: (rewardId: string, code: string) => Promise<{ redeemed_at: string }>;
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
      request(`/v1/customers/identify`, {
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
      request<{ redeemed_at: string }>(`/v1/rewards/${rewardId}/validate`, {
        method: "POST",
        body: JSON.stringify({ validation_code: code }),
      }),
  };
}

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

export interface ActiveCampaign {
  id: string;
  name: string;
  multiplier: number;
  ends_at: string;
}

export interface TapResponse {
  tenant: TenantPublic;
  customer: CustomerSnapshot | null;
  tap_id: string;
  stamp_awarded: boolean;
  stamps_current: number;
  reward_state: RewardStateSnapshot;
  reward_available: RewardAvailable | null;
  active_campaign: ActiveCampaign | null;
  stamps_awarded_count: number;
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

export type TrialStatus =
  | "active"
  | "expiring_soon"
  | "expired"
  | "subscribed"
  | "inactive";

export interface TenantSummary {
  id: string;
  slug: string;
  name: string;
  business_type: BusinessType;
  plan: TenantPlan;
  is_active: boolean;
  trial_ends_at: string | null;
  onboarding_complete: boolean;
  trial_status: TrialStatus;
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

export type BillingPlanId = "review" | "loyalty" | "pro" | "network";

export type CampaignType = "double_stamp" | "reactivation" | "birthday" | "custom";
export type CampaignStatus = "draft" | "active" | "paused" | "ended";

export interface Campaign {
  id: string;
  tenant_id: string;
  name: string;
  type: CampaignType;
  status: CampaignStatus;
  multiplier: number;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
}

export interface CampaignCreateInput {
  name: string;
  // S4-W1 only supports double_stamp; widen the union as new types ship.
  type?: "double_stamp";
  multiplier: number;
  starts_at: string;
  ends_at: string;
  status?: "draft" | "active";
}

export interface CampaignUpdateInput {
  name?: string;
  multiplier?: number;
  starts_at?: string;
  ends_at?: string;
}

// ---------------------------------------------------------------------------
// Segments (S4-W4)
// ---------------------------------------------------------------------------

/**
 * All fields optional — null/undefined = criterion not applied. The engine
 * combines every set field with AND semantics. `..._after_days` means
 * "event is within the last N days" (recent); `..._before_days` means
 * "event is older than N days" (dormant).
 */
export interface SegmentCriteria {
  visits_min?: number | null;
  visits_max?: number | null;
  stamps_min?: number | null;
  stamps_max?: number | null;
  last_visit_after_days?: number | null;
  last_visit_before_days?: number | null;
  created_after_days?: number | null;
  has_email?: boolean | null;
  has_phone?: boolean | null;
  /** Only meaningful as `true`. The backend rejects `false` to avoid
   * mass-targeting customers who haven't consented. */
  gdpr_consent_only?: boolean | null;
}

export interface Segment {
  id: string;
  tenant_id: string;
  name: string;
  criteria: SegmentCriteria;
  created_at: string;
  updated_at: string;
}

export interface SegmentCreateInput {
  name: string;
  criteria: SegmentCriteria;
}

export interface SegmentUpdateInput {
  name?: string;
  criteria?: SegmentCriteria;
}

export interface SegmentCustomerPreview {
  id: string;
  name: string | null;
  phone: string | null;
  email: string | null;
  current_stamps: number;
  total_visits: number;
  last_visit_at: string | null;
  created_at: string;
}

export interface SegmentPreview {
  total: number;
  items: SegmentCustomerPreview[];
  evaluated_at: string;
}

export interface CheckoutSessionInput {
  plan: BillingPlanId;
  success_url: string;
  cancel_url: string;
}

export interface PortalSessionInput {
  return_url: string;
}

export interface SubscriptionInfo {
  plan: TenantPlan;
  is_active: boolean;
  is_founding_member: boolean;
  trial_ends_at: string | null;
  cancelled_at: string | null;
  has_subscription: boolean;
  status: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean | null;
  trial_status: TrialStatus;
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
  optOutCustomer: (magicLinkToken: string) => Promise<void>;
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
  downloadMonthlyReport: (params?: {
    year?: number;
    month?: number;
  }) => Promise<{ blob: Blob; filename: string }>;
  completeOnboarding: (body: OnboardingComplete) => Promise<TenantSummary>;
  createCheckoutSession: (body: CheckoutSessionInput) => Promise<{ url: string }>;
  createPortalSession: (body: PortalSessionInput) => Promise<{ url: string }>;
  getSubscription: () => Promise<SubscriptionInfo>;
  listCampaigns: () => Promise<{ items: Campaign[] }>;
  createCampaign: (body: CampaignCreateInput) => Promise<Campaign>;
  updateCampaign: (id: string, body: CampaignUpdateInput) => Promise<Campaign>;
  changeCampaignStatus: (id: string, status: CampaignStatus) => Promise<Campaign>;
  listSegments: () => Promise<{ items: Segment[] }>;
  createSegment: (body: SegmentCreateInput) => Promise<Segment>;
  updateSegment: (id: string, body: SegmentUpdateInput) => Promise<Segment>;
  deleteSegment: (id: string) => Promise<void>;
  previewSegment: (id: string, limit?: number) => Promise<SegmentPreview>;
  previewUnsavedSegment: (
    body: SegmentCreateInput,
    limit?: number,
  ) => Promise<SegmentPreview>;
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
      // Prefer the user-facing message from the body (BusinessError handler
      // sets `error.message`); fall back to the HTTP statusText.
      const businessMessage =
        body && typeof body === "object" && "error" in body
          ? ((body as BusinessErrorBody).error?.message ?? null)
          : null;
      throw new ApiError(res.status, businessMessage ?? res.statusText, body);
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

  async function requestBlob(
    path: string,
    init: RequestInit = {},
  ): Promise<{ blob: Blob; filename: string | null }> {
    // Binary download path — used for PDF/CSV streamed responses. Mirrors
    // requestText for auth/headers but reads as Blob and pulls the suggested
    // filename out of Content-Disposition so callers can save with the
    // backend-chosen name (avoids drift between two filename conventions).
    const headers: Record<string, string> = {
      ...(init.headers as Record<string, string> | undefined),
    };
    if (opts.getToken) {
      const token = await opts.getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetchImpl(`${baseUrl}${path}`, { ...init, headers });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new ApiError(res.status, res.statusText, text);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") ?? "";
    const match = /filename="?([^"]+)"?/i.exec(disposition);
    // `match[1]` is typed as `string | undefined` because of TS's strict
    // noUncheckedIndexedAccess. Normalise undefined -> null so callers only
    // have to handle one missing-value shape.
    return { blob, filename: match?.[1] ?? null };
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
    optOutCustomer: async (magicLinkToken) => {
      // 204 No Content — request<T> assumes a JSON body, so use requestText
      // and discard. Idempotent on the server: hitting it twice still 204s.
      await requestText(`/v1/customers/opt-out/${encodeURIComponent(magicLinkToken)}`, {
        method: "POST",
      });
    },
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
    downloadMonthlyReport: async (params) => {
      const qs = new URLSearchParams();
      if (params?.year !== undefined) qs.set("year", String(params.year));
      if (params?.month !== undefined) qs.set("month", String(params.month));
      const suffix = qs.toString() ? `?${qs.toString()}` : "";
      const { blob, filename } = await requestBlob(
        `/v1/reports/monthly.pdf${suffix}`,
      );
      // The backend always sets Content-Disposition with a filename. Falling
      // back to a generic name here is defensive — if the header ever goes
      // missing the download still works rather than throwing.
      return { blob, filename: filename ?? "smarttap-monthly-report.pdf" };
    },
    completeOnboarding: (body) =>
      request<TenantSummary>(`/v1/onboarding/complete`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    createCheckoutSession: (body) =>
      request<{ url: string }>(`/v1/billing/checkout-session`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    createPortalSession: (body) =>
      request<{ url: string }>(`/v1/billing/portal-session`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    getSubscription: () => request<SubscriptionInfo>(`/v1/billing/subscription`),
    listCampaigns: () => request<{ items: Campaign[] }>(`/v1/campaigns`),
    createCampaign: (body) =>
      request<Campaign>(`/v1/campaigns`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    updateCampaign: (id, body) =>
      request<Campaign>(`/v1/campaigns/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    changeCampaignStatus: (id, status) =>
      request<Campaign>(`/v1/campaigns/${id}/status`, {
        method: "POST",
        body: JSON.stringify({ status }),
      }),
    listSegments: () => request<{ items: Segment[] }>(`/v1/segments`),
    createSegment: (body) =>
      request<Segment>(`/v1/segments`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    updateSegment: (id, body) =>
      request<Segment>(`/v1/segments/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    deleteSegment: async (id) => {
      // 204 No Content — request<T> assumes JSON, so use requestText and
      // discard. Hard delete on the server (see segment_service).
      await requestText(`/v1/segments/${id}`, { method: "DELETE" });
    },
    previewSegment: (id, limit) => {
      const qs = limit ? `?limit=${limit}` : "";
      return request<SegmentPreview>(`/v1/segments/${id}/preview${qs}`);
    },
    previewUnsavedSegment: (body, limit) => {
      const qs = limit ? `?limit=${limit}` : "";
      return request<SegmentPreview>(`/v1/segments/preview${qs}`, {
        method: "POST",
        body: JSON.stringify(body),
      });
    },
  };
}

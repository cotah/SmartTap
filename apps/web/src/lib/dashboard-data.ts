import "server-only";

import { redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, getAuthApiClient } from "./api";
import type { MeResponse, TenantSummary } from "./api";
import { getAccessToken } from "./auth";

export interface OnboardingContext {
  user_id: string;
  email: string | null;
  tenant: TenantSummary;
  /** All memberships — drives the tenant switcher when there is more than one. */
  tenants: TenantSummary[];
}

// Same shape as OnboardingContext; the difference is the runtime guarantee
// that tenant.onboarding_complete is true when this type is returned.
export type DashboardContext = OnboardingContext;

/**
 * Auth + bootstrap (creates tenant if missing) without enforcing onboarding.
 * Use this on /onboarding itself; everywhere else use `getDashboardContext`.
 */
export const getOnboardingContext = cache(async (): Promise<OnboardingContext> => {
  const token = await getAccessToken();
  if (!token) {
    redirect("/login");
  }
  const api = getAuthApiClient();
  let me: MeResponse;
  try {
    me = await api.getMe();
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      redirect("/login");
    }
    throw err;
  }

  let tenant = me.tenant;
  let tenants = me.tenants;
  if (tenant === null) {
    const result = await api.bootstrapMe({});
    tenant = result.tenant;
    tenants = [result.tenant];
  }

  return { user_id: me.user_id, email: me.email, tenant, tenants };
});

export const getDashboardContext = cache(async (): Promise<DashboardContext> => {
  const ctx = await getOnboardingContext();
  if (!ctx.tenant.onboarding_complete) {
    redirect("/onboarding");
  }
  return ctx;
});

import "server-only";

import { redirect } from "next/navigation";
import { cache } from "react";

import { ApiError, getAuthApiClient } from "./api";
import type { MeResponse, TenantSummary } from "./api";
import { getAccessToken } from "./auth";

export interface DashboardContext {
  user_id: string;
  email: string | null;
  tenant: TenantSummary;
}

export const getDashboardContext = cache(async (): Promise<DashboardContext> => {
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
  if (tenant === null) {
    const result = await api.bootstrapMe({});
    tenant = result.tenant;
  }

  return { user_id: me.user_id, email: me.email, tenant };
});

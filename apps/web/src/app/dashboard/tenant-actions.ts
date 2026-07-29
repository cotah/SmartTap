"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { ACTIVE_TENANT_COOKIE, ApiError, getAuthApiClient } from "@/lib/api";

export type SwitchTenantResult = { ok: true } | { ok: false; message: string };

/**
 * Persist the active tenant for multi-tenant users. Validates membership
 * before setting the cookie so a bad id can never wedge the dashboard into
 * a 403 loop (the backend re-validates on every call anyway).
 */
export async function switchTenantAction(
  tenantId: string,
): Promise<SwitchTenantResult> {
  try {
    const api = getAuthApiClient();
    const me = await api.getMe();
    if (!me.tenants.some((t) => t.id === tenantId)) {
      return { ok: false, message: "You are not a member of that business." };
    }
  } catch (err) {
    if (err instanceof ApiError) {
      return { ok: false, message: err.message || "Could not switch business." };
    }
    return { ok: false, message: "Could not switch business. Try again." };
  }

  (await cookies()).set(ACTIVE_TENANT_COOKIE, tenantId, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
  });
  revalidatePath("/dashboard");
  return { ok: true };
}

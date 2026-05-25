"use server";

import { redirect } from "next/navigation";
import { z } from "zod";

import { publicEnv } from "@/lib/env";
import { createSupabaseServerClient } from "@/lib/supabase/server";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters"),
  business_name: z
    .string()
    .min(2, "Business name needs at least 2 characters")
    .max(80, "Too long")
    .optional()
    .or(z.literal("").transform(() => undefined)),
  next: z.string().default("/dashboard"),
});

async function bootstrapTenant(
  accessToken: string,
  businessName: string | undefined,
): Promise<void> {
  try {
    await fetch(`${publicEnv.NEXT_PUBLIC_API_URL}/v1/me/bootstrap`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ business_name: businessName ?? null }),
    });
  } catch (err) {
    console.error("bootstrap_failed_post_signup", err);
  }
}

export async function signUpAction(
  formData: FormData,
): Promise<{ error: string } | undefined> {
  const raw = Object.fromEntries(formData);
  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    return { error: parsed.error.errors[0]?.message ?? "Invalid data" };
  }
  const { email, password, business_name, next } = parsed.data;

  const supabase = await createSupabaseServerClient();
  const { data, error } = await supabase.auth.signUp({ email, password });
  if (error) {
    return { error: error.message };
  }

  const accessToken =
    data.session?.access_token ??
    (await supabase.auth.getSession()).data.session?.access_token;

  if (accessToken) {
    await bootstrapTenant(accessToken, business_name);
  }

  const safeNext = next.startsWith("/") ? next : "/dashboard";
  redirect(safeNext);
}

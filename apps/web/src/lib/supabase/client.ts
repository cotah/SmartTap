"use client";

import { createBrowserClient } from "@supabase/ssr";

/**
 * NEXT_PUBLIC_* env vars are baked into the client bundle at build time.
 * If they're missing in the build environment (Vercel project settings,
 * local `.env.local`, etc.) the client will throw on first call instead
 * of silently constructing an invalid Supabase client. That throw
 * surfaces as "a client-side exception has occurred" on /signup and
 * /login when the user submits the form — a recoverable signal that
 * production env vars aren't configured.
 *
 * Fix path: `vercel env add NEXT_PUBLIC_SUPABASE_URL production` +
 * `NEXT_PUBLIC_SUPABASE_ANON_KEY`, then redeploy so the new values are
 * baked into the bundle.
 */
export function createSupabaseBrowserClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) {
    throw new Error(
      "Supabase env vars missing — set NEXT_PUBLIC_SUPABASE_URL and " +
        "NEXT_PUBLIC_SUPABASE_ANON_KEY in your Vercel project (or " +
        ".env.local for dev), then redeploy to bake them into the client bundle.",
    );
  }
  return createBrowserClient(url, anonKey);
}

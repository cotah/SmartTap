"use client";

import Link from "next/link";
import { type FormEvent, useState, useTransition } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function SignupForm() {
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const email = String(fd.get("email") ?? "");
    const password = String(fd.get("password") ?? "");
    const businessName = String(fd.get("business_name") ?? "").trim() || null;
    setError(null);
    startTransition(async () => {
      const supabase = createSupabaseBrowserClient();
      const { data, error: err } = await supabase.auth.signUp({ email, password });
      if (err) {
        setError(err.message);
        return;
      }
      const token = data.session?.access_token;
      if (token) {
        try {
          await fetch(`${API_URL}/v1/me/bootstrap`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ business_name: businessName }),
          });
        } catch (e) {
          console.error("bootstrap_failed_post_signup", e);
        }
      }
      window.location.href = "/dashboard";
    });
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <label className="flex flex-col gap-1 text-sm">
        <span>Email</span>
        <input
          type="email"
          name="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          className="rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span>Password</span>
        <input
          type="password"
          name="password"
          required
          minLength={8}
          autoComplete="new-password"
          placeholder="At least 8 characters"
          className="rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span>
          Business name <span className="text-muted-foreground">(optional)</span>
        </span>
        <input
          type="text"
          name="business_name"
          autoComplete="organization"
          placeholder="Joe's Barbers"
          className="rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
        <span className="text-xs text-muted-foreground">
          You can change this later in Settings.
        </span>
      </label>

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <button
        type="submit"
        disabled={pending}
        className="mt-2 rounded-full bg-brand-green px-6 py-3 font-semibold text-brand-off-white disabled:opacity-60"
      >
        {pending ? "Creating account…" : "Create account"}
      </button>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="font-semibold text-brand-green underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}

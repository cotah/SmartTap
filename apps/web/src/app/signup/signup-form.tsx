"use client";

import { Briefcase, Lock, Mail } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useState, useTransition } from "react";

import { GoogleButton, OrDivider } from "@/components/google-button";
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
    <div className="flex flex-col gap-5">
      <GoogleButton next="/dashboard" label="Sign up with Google" />
      <OrDivider />

      <form onSubmit={onSubmit} className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <label
            htmlFor="signup-email"
            className="text-xs font-bold uppercase tracking-wider text-brand-black"
          >
            Email address
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-600">
              <Mail className="h-5 w-5" aria-hidden="true" />
            </span>
            <input
              id="signup-email"
              type="email"
              name="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              className={INPUT_CLASS}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label
            htmlFor="signup-password"
            className="text-xs font-bold uppercase tracking-wider text-brand-black"
          >
            Password
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-600">
              <Lock className="h-5 w-5" aria-hidden="true" />
            </span>
            <input
              id="signup-password"
              type="password"
              name="password"
              required
              minLength={8}
              autoComplete="new-password"
              placeholder="At least 8 characters"
              className={INPUT_CLASS}
            />
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label
            htmlFor="signup-business"
            className="text-xs font-bold uppercase tracking-wider text-brand-black"
          >
            Business name{" "}
            <span className="text-neutral-600/70 normal-case">(optional)</span>
          </label>
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-neutral-600">
              <Briefcase className="h-5 w-5" aria-hidden="true" />
            </span>
            <input
              id="signup-business"
              type="text"
              name="business_name"
              autoComplete="organization"
              placeholder="Joe's Barbers"
              className={INPUT_CLASS}
            />
          </div>
          <p className="text-xs text-neutral-600">
            You can change this later in Settings.
          </p>
        </div>

        {error ? (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={pending}
          className="mt-2 w-full rounded-lg bg-brand-green px-6 py-4 text-sm font-bold uppercase tracking-wider text-white shadow-sm transition-colors hover:bg-green-800 active:scale-[0.98] disabled:opacity-60"
        >
          {pending ? "Creating account…" : "Create account"}
        </button>

        <p className="mt-2 text-center text-sm text-neutral-600">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-bold text-brand-green transition-colors hover:text-brand-amber"
          >
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}

const INPUT_CLASS =
  "block w-full rounded-lg border border-transparent bg-brand-off-white py-3 pl-10 pr-3 text-base text-brand-black shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] outline-none transition-colors placeholder:text-neutral-600/40 focus:border-brand-amber focus:ring-2 focus:ring-brand-amber/40";

"use client";

import { useState, useTransition } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

interface Props {
  /** Path to send the user to after the OAuth round-trip lands on /auth/callback. */
  next?: string;
  /** Label override. Default suits sign-in; signup may want "Sign up with Google". */
  label?: string;
  /**
   * Optional className override on the outer button. The default styles are
   * Dark Electric (full-width, dark surface-2 card with electric border,
   * lifts on hover with a cyan-tinted glow).
   */
  className?: string;
}

/**
 * Single source of truth for "Continue with Google" across /login and
 * /signup. Uses Supabase's signInWithOAuth which redirects to Google,
 * then back to our /auth/callback?code=...&next=... handler, which
 * exchanges the code for a session and redirects to `next`.
 *
 * IMPORTANT: do not use this in customer-facing flows (/t/[uuid]).
 * Supabase OAuth creates an authenticated user in the same pool as
 * tenant owners — and the dashboard layout would happily bootstrap a
 * tenant for them. Customer identification belongs to phone/SMS (the
 * remarketing channel anyway) — see Sprint 5.6 OTP.
 */
export function GoogleButton({
  next = "/dashboard",
  label = "Continue with Google",
  className,
}: Props) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function onClick() {
    setError(null);
    startTransition(async () => {
      const supabase = createSupabaseBrowserClient();
      const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
      const { error: err } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo },
      });
      if (err) {
        setError(err.message);
      }
      // On success the browser is navigating away — no further state
      // updates are needed (and would warn about unmounted setState).
    });
  }

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={onClick}
        disabled={pending}
        aria-label={label}
        className={
          className ??
          "group flex w-full items-center justify-center gap-3 rounded-lg border border-electric-border bg-electric-surface-2 px-4 py-3.5 text-sm font-medium text-electric-text shadow-sm transition-all hover:-translate-y-0.5 hover:border-electric-cyan hover:shadow-[0_4px_12px_rgba(0,212,255,0.15)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
        }
      >
        <GoogleLogo />
        <span>{pending ? "Redirecting…" : label}</span>
      </button>
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}

function GoogleLogo() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden="true"
    >
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

/**
 * Stand-alone "or" divider for placing between the GoogleButton and
 * the email/password form. Use it inside the same parent that owns
 * the form gap.
 */
export function OrDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="relative flex items-center" aria-hidden="true">
      <div className="flex-1 border-t border-electric-border" />
      <span className="px-3 text-[10px] font-bold uppercase tracking-widest text-electric-text-muted">
        {label}
      </span>
      <div className="flex-1 border-t border-electric-border" />
    </div>
  );
}

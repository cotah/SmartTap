"use client";

import { useTransition } from "react";

import { signOutAction } from "./actions";

export function SignOutButton() {
  const [pending, startTransition] = useTransition();
  return (
    <form action={() => startTransition(() => signOutAction())}>
      <button
        type="submit"
        disabled={pending}
        className="text-sm font-medium text-electric-text-muted underline transition-colors hover:text-electric-cyan disabled:opacity-60"
      >
        {pending ? "Signing out…" : "Sign out"}
      </button>
    </form>
  );
}

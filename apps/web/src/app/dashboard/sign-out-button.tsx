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
        className="text-sm font-medium text-neutral-600 underline transition-colors hover:text-brand-green disabled:opacity-60"
      >
        {pending ? "Signing out…" : "Sign out"}
      </button>
    </form>
  );
}

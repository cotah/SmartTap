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
        className="text-sm text-brand-black/70 underline hover:text-brand-green disabled:opacity-60"
      >
        {pending ? "Signing out…" : "Sign out"}
      </button>
    </form>
  );
}

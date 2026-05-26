"use client";

import { useEffect, useState } from "react";

import { optOutAction, type OptOutResult } from "./actions";

type Status = "pending" | "running" | "done" | "failed";

interface Props {
  token: string;
}

/**
 * Client component because we need the user-initiated POST to happen
 * post-hydration — a server-side auto-POST on first GET would let any link
 * preview crawler unsubscribe the customer accidentally (Gmail, iMessage,
 * Slack all fetch the URL when showing the link). We require a click.
 */
export function OptOutView({ token }: Props) {
  const [status, setStatus] = useState<Status>("pending");
  const [result, setResult] = useState<OptOutResult | null>(null);

  // Auto-submit on mount has the same crawler-preview problem; keep it
  // strictly user-initiated. The button below is the actual trigger.
  useEffect(() => {
    // no-op; here so future telemetry hooks have a place to live
  }, []);

  async function handleClick() {
    setStatus("running");
    const res = await optOutAction(token);
    setResult(res);
    setStatus(res.ok ? "done" : "failed");
  }

  if (status === "done") {
    return (
      <section className="space-y-3 text-center">
        <h1 className="font-display text-2xl">You&apos;re unsubscribed</h1>
        <p className="text-sm text-brand-black/70">
          We won&apos;t send you any more reactivation emails. Your stamps are
          still safe — visit the shop to keep collecting them.
        </p>
      </section>
    );
  }

  if (status === "failed" && result && !result.ok) {
    return (
      <section className="space-y-3 text-center">
        <h1 className="font-display text-2xl">Couldn&apos;t complete that</h1>
        <p className="text-sm text-brand-black/70">{result.error}</p>
        {result.status !== 404 && (
          <button
            type="button"
            onClick={handleClick}
            className="rounded-full bg-brand-green px-5 py-2 text-sm font-semibold text-brand-off-white"
          >
            Try again
          </button>
        )}
      </section>
    );
  }

  return (
    <section className="space-y-4 text-center">
      <h1 className="font-display text-2xl">Unsubscribe from reactivation emails</h1>
      <p className="text-sm text-brand-black/70">
        Click below to stop receiving these messages. Your loyalty stamps stay
        on file — we just won&apos;t email you about them again.
      </p>
      <button
        type="button"
        onClick={handleClick}
        disabled={status === "running"}
        className="rounded-full bg-brand-green px-5 py-2 text-sm font-semibold text-brand-off-white disabled:opacity-60"
      >
        {status === "running" ? "Unsubscribing…" : "Unsubscribe me"}
      </button>
    </section>
  );
}

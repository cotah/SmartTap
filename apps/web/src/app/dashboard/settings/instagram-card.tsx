"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { InstagramStatus } from "@/lib/api";

import { connectInstagramAction, disconnectInstagramAction } from "./actions";

/**
 * Connect/disconnect card for the Instagram DM assistant. Mirrors the Google
 * Business card on /dashboard/reviews. `callbackResult` reflects the
 * ?instagram_connected=1/0 query param set by the OAuth callback redirect.
 */
export function InstagramCard({
  status,
  callbackResult,
}: {
  status: InstagramStatus;
  callbackResult: "success" | "error" | null;
}) {
  return (
    <div className="space-y-3">
      {callbackResult === "success" ? (
        <p
          role="status"
          className="rounded-lg bg-electric-cyan/10 px-4 py-3 text-sm text-electric-cyan"
        >
          Instagram connected. The assistant will now reply to your DMs.
        </p>
      ) : null}
      {callbackResult === "error" ? (
        <p
          role="status"
          className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-300"
        >
          Instagram connection failed. Please try again.
        </p>
      ) : null}

      {status.connected ? (
        <ConnectedCard
          accountId={status.instagram_business_account_id}
          connectedAt={status.connected_at}
        />
      ) : (
        <DisconnectedCard />
      )}
    </div>
  );
}

function DisconnectedCard() {
  const [error, setError] = useState<string | null>(null);
  const [connecting, startConnect] = useTransition();

  function handleConnect() {
    setError(null);
    startConnect(async () => {
      const res = await connectInstagramAction();
      if (res.ok) {
        window.location.href = res.url;
      } else {
        setError(res.message);
      }
    });
  }

  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-electric-border bg-electric-surface p-4 md:flex-row md:items-center md:justify-between">
      <div>
        <p className="font-display text-lg">Instagram DM assistant</p>
        <p className="text-sm text-electric-text-muted">
          Connect your Instagram business account and SmartTap will auto-reply
          to DMs and story mentions using AI.
        </p>
        {error ? <p className="mt-1 text-sm text-red-300">{error}</p> : null}
      </div>
      <button
        type="button"
        onClick={handleConnect}
        disabled={connecting}
        className="shrink-0 rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg disabled:opacity-60"
      >
        {connecting ? "Connecting…" : "Connect Instagram"}
      </button>
    </div>
  );
}

function ConnectedCard({
  accountId,
  connectedAt,
}: {
  accountId?: string | null;
  connectedAt?: string | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function handleDisconnect() {
    setError(null);
    startTransition(async () => {
      const res = await disconnectInstagramAction();
      if (res.ok) {
        router.refresh();
      } else {
        setError(res.message);
      }
    });
  }

  const since = connectedAt
    ? new Date(connectedAt).toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4 md:flex-row md:items-center md:justify-between">
      <div>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-semibold text-emerald-300">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden />
          Connected
        </span>
        <p className="mt-2 font-display text-lg">Instagram DM assistant</p>
        <p className="text-sm text-electric-text-muted">
          SmartTap auto-replies to your DMs and story mentions
          {accountId ? ` · account ${accountId}` : ""}
          {since ? ` · since ${since}` : ""}.
        </p>
        {error ? <p className="mt-1 text-sm text-red-300">{error}</p> : null}
      </div>
      <button
        type="button"
        onClick={handleDisconnect}
        disabled={pending}
        className="shrink-0 rounded-full border border-electric-border px-5 py-2.5 text-sm font-semibold text-electric-text-muted disabled:opacity-60"
      >
        {pending ? "Disconnecting…" : "Disconnect"}
      </button>
    </div>
  );
}

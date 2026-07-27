"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { InstagramPage, InstagramStatus } from "@/lib/api";

import {
  connectInstagramAction,
  disconnectInstagramAction,
  selectInstagramPageAction,
} from "./actions";

/**
 * Connect/disconnect card for the Instagram DM assistant. Mirrors the Google
 * Business card on /dashboard/reviews. `callbackResult` reflects the
 * ?instagram_connected=1/0 query param set by the OAuth callback redirect.
 * `pendingPages` is non-null when the callback redirected with
 * ?instagram_select=1 (more than one eligible Facebook Page) — the card then
 * renders the Page Picker; an empty list means the selection expired.
 */
export function InstagramCard({
  status,
  callbackResult,
  pendingPages,
}: {
  status: InstagramStatus;
  callbackResult: "success" | "error" | null;
  pendingPages: InstagramPage[] | null;
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

      {pendingPages !== null ? (
        pendingPages.length > 0 ? (
          <PickerCard pages={pendingPages} />
        ) : (
          <>
            <p
              role="status"
              className="rounded-lg bg-amber-500/10 px-4 py-3 text-sm text-amber-300"
            >
              Your page selection expired. Please connect Instagram again.
            </p>
            <DisconnectedCard />
          </>
        )
      ) : status.connected ? (
        <ConnectedCard
          accountId={status.instagram_business_account_id}
          connectedAt={status.connected_at}
          pageName={status.page_name}
          igUsername={status.ig_username}
        />
      ) : (
        <DisconnectedCard />
      )}
    </div>
  );
}

/**
 * Page Picker — the tenant's Facebook login manages more than one eligible
 * Page, so the OAuth callback parked a pending connection and we let the
 * owner choose which Page/Instagram account SmartTap should answer for.
 */
function PickerCard({ pages }: { pages: InstagramPage[] }) {
  const router = useRouter();
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function handleConfirm() {
    if (!selected) return;
    setError(null);
    startTransition(async () => {
      const res = await selectInstagramPageAction(selected);
      if (res.ok) {
        // Drop ?instagram_select=1 and show the success banner. The action
        // already revalidated the page, so this re-renders as connected.
        router.replace("/dashboard/settings?instagram_connected=1");
      } else {
        setError(res.message);
      }
    });
  }

  return (
    <div className="rounded-2xl border border-electric-border bg-electric-surface p-4">
      <p className="font-display text-lg">Choose your Instagram account</p>
      <p className="text-sm text-electric-text-muted">
        Your Facebook login manages more than one Page. Pick the one SmartTap
        should reply for.
      </p>

      <fieldset className="mt-3 space-y-2" disabled={pending}>
        <legend className="sr-only">Facebook Pages with an Instagram business account</legend>
        {pages.map((page) => (
          <label
            key={page.facebook_page_id}
            className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition-colors ${
              selected === page.facebook_page_id
                ? "border-electric-cyan bg-electric-cyan/10"
                : "border-electric-border"
            }`}
          >
            <input
              type="radio"
              name="instagram-page"
              value={page.facebook_page_id}
              checked={selected === page.facebook_page_id}
              onChange={() => setSelected(page.facebook_page_id)}
              className="h-4 w-4 accent-[#00D4FF]"
            />
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">
                {page.page_name ?? `Page ${page.facebook_page_id}`}
              </span>
              <span className="block truncate text-xs text-electric-text-muted">
                {page.ig_username
                  ? `@${page.ig_username}`
                  : `Instagram account ${page.instagram_business_account_id}`}
              </span>
            </span>
          </label>
        ))}
      </fieldset>

      {error ? <p className="mt-2 text-sm text-red-300">{error}</p> : null}

      <button
        type="button"
        onClick={handleConfirm}
        disabled={pending || !selected}
        className="mt-4 rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg disabled:opacity-60"
      >
        {pending ? "Connecting…" : "Confirm"}
      </button>
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
  pageName,
  igUsername,
}: {
  accountId?: string | null;
  connectedAt?: string | null;
  pageName?: string | null;
  igUsername?: string | null;
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

  // Prefer human-readable identity (set by the Page Picker flow); fall back
  // to the raw account id for connections made before migration 017.
  const account = igUsername
    ? `@${igUsername}`
    : (pageName ?? (accountId ? `account ${accountId}` : null));

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
          {account ? ` · ${account}` : ""}
          {igUsername && pageName ? ` (${pageName})` : ""}
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

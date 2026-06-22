"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { GoogleStatus, Review } from "@/lib/api";

import {
  connectGoogleAction,
  disconnectGoogleAction,
  dismissReviewAction,
  publishReviewAction,
} from "./actions";

export function ReviewsClient({
  reviews,
  googleStatus,
}: {
  reviews: Review[];
  googleStatus: GoogleStatus;
}) {
  // Local copy so published/dismissed reviews disappear immediately; the
  // server action also revalidates the route for the next navigation.
  const [items, setItems] = useState<Review[]>(reviews);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [connecting, startConnect] = useTransition();

  function handleConnect() {
    setConnectError(null);
    startConnect(async () => {
      const res = await connectGoogleAction();
      if (res.ok) {
        window.location.href = res.url;
      } else {
        setConnectError(res.message);
      }
    });
  }

  function removeItem(id: string) {
    setItems((prev) => prev.filter((r) => r.id !== id));
  }

  return (
    <div className="space-y-6">
      {googleStatus.connected ? (
        <ConnectedCard
          accountName={googleStatus.account_name}
          connectedAt={googleStatus.connected_at}
        />
      ) : (
        <div className="flex flex-col gap-2 rounded-2xl border border-electric-border bg-electric-surface p-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-display text-lg">Connect Google Business</p>
            <p className="text-sm text-electric-text-muted">
              Authorise SmartTap to read your reviews and post your approved
              replies.
            </p>
            {connectError ? (
              <p className="mt-1 text-sm text-red-300">{connectError}</p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleConnect}
            disabled={connecting}
            className="shrink-0 rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg disabled:opacity-60"
          >
            {connecting ? "Connecting…" : "Connect Google"}
          </button>
        </div>
      )}

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="space-y-4">
          {items.map((review) => (
            <li key={review.id}>
              <ReviewCard review={review} onResolved={() => removeItem(review.id)} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ConnectedCard({
  accountName,
  connectedAt,
}: {
  accountName?: string | null;
  connectedAt?: string | null;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function handleDisconnect() {
    setError(null);
    startTransition(async () => {
      const res = await disconnectGoogleAction();
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
        <p className="mt-2 font-display text-lg">
          {accountName ?? "Google Business connected"}
        </p>
        <p className="text-sm text-electric-text-muted">
          SmartTap reads your reviews and posts replies you approve
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

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-electric-border bg-electric-surface p-8 text-center">
      <p className="font-display text-lg">No reviews waiting</p>
      <p className="mt-1 text-sm text-electric-text-muted">
        When new Google reviews come in, a suggested reply will appear here for
        you to approve.
      </p>
    </div>
  );
}

function ReviewCard({
  review,
  onResolved,
}: {
  review: Review;
  onResolved: () => void;
}) {
  const [reply, setReply] = useState<string>(
    review.reply_text ?? review.ai_draft ?? "",
  );
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const isNegative = (review.rating ?? 0) > 0 && (review.rating ?? 0) <= 2;

  function handlePublish() {
    setError(null);
    startTransition(async () => {
      const res = await publishReviewAction(review.id, reply);
      if (res.ok) {
        onResolved();
      } else {
        setError(res.message);
      }
    });
  }

  function handleDismiss() {
    setError(null);
    startTransition(async () => {
      const res = await dismissReviewAction(review.id);
      if (res.ok) {
        onResolved();
      } else {
        setError(res.message);
      }
    });
  }

  return (
    <div
      className={`rounded-2xl border bg-electric-surface p-4 shadow-sm ${
        isNegative ? "border-red-300" : "border-electric-border"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-display text-lg">{review.author ?? "Anonymous"}</p>
          <Stars rating={review.rating} />
        </div>
        {isNegative ? (
          <span className="rounded-full bg-red-500/15 px-2.5 py-1 text-xs font-semibold text-red-300">
            Needs care
          </span>
        ) : null}
      </div>

      {review.comment ? (
        <p className="mt-3 whitespace-pre-wrap text-sm text-electric-text-muted">
          {review.comment}
        </p>
      ) : (
        <p className="mt-3 text-sm italic text-electric-text-muted">No written comment</p>
      )}

      <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
        Suggested reply (edit before publishing)
      </label>
      <textarea
        value={reply}
        onChange={(e) => setReply(e.target.value)}
        rows={4}
        className="mt-1 w-full rounded-xl border border-electric-border p-3 text-sm focus:border-electric-cyan focus:outline-none"
        placeholder="Write a reply…"
      />

      {error ? <p className="mt-2 text-sm text-red-300">{error}</p> : null}

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={handlePublish}
          disabled={pending}
          className="rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg disabled:opacity-60"
        >
          {pending ? "Working…" : "Publish to Google"}
        </button>
        <button
          type="button"
          onClick={handleDismiss}
          disabled={pending}
          className="rounded-full border border-electric-border px-5 py-2 text-sm font-semibold text-electric-text-muted disabled:opacity-60"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

function Stars({ rating }: { rating: number | null }) {
  const r = rating ?? 0;
  return (
    <p className="mt-0.5 text-sm text-electric-cyan" aria-label={`${r} out of 5 stars`}>
      {"★".repeat(r)}
      <span className="text-electric-text-muted">{"★".repeat(Math.max(0, 5 - r))}</span>
    </p>
  );
}

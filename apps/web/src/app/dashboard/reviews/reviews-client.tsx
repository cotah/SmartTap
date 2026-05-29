"use client";

import { useState, useTransition } from "react";

import type { Review } from "@/lib/api";

import {
  connectGoogleAction,
  dismissReviewAction,
  publishReviewAction,
} from "./actions";

export function ReviewsClient({ reviews }: { reviews: Review[] }) {
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
      <div className="flex flex-col gap-2 rounded-2xl border border-brand-black/10 bg-white p-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-display text-lg">Connect Google Business</p>
          <p className="text-sm text-brand-black/60">
            Authorise SmartTap to read your reviews and post your approved
            replies.
          </p>
          {connectError ? (
            <p className="mt-1 text-sm text-red-600">{connectError}</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={handleConnect}
          disabled={connecting}
          className="shrink-0 rounded-full bg-brand-green px-5 py-2.5 text-sm font-semibold text-brand-off-white disabled:opacity-60"
        >
          {connecting ? "Connecting…" : "Connect Google"}
        </button>
      </div>

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

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-brand-black/20 bg-white p-8 text-center">
      <p className="font-display text-lg">No reviews waiting</p>
      <p className="mt-1 text-sm text-brand-black/60">
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
      className={`rounded-2xl border bg-white p-4 shadow-sm ${
        isNegative ? "border-red-300" : "border-brand-black/10"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-display text-lg">{review.author ?? "Anonymous"}</p>
          <Stars rating={review.rating} />
        </div>
        {isNegative ? (
          <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700">
            Needs care
          </span>
        ) : null}
      </div>

      {review.comment ? (
        <p className="mt-3 whitespace-pre-wrap text-sm text-brand-black/80">
          {review.comment}
        </p>
      ) : (
        <p className="mt-3 text-sm italic text-brand-black/40">No written comment</p>
      )}

      <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-brand-black/50">
        Suggested reply (edit before publishing)
      </label>
      <textarea
        value={reply}
        onChange={(e) => setReply(e.target.value)}
        rows={4}
        className="mt-1 w-full rounded-xl border border-brand-black/15 p-3 text-sm focus:border-brand-green focus:outline-none"
        placeholder="Write a reply…"
      />

      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}

      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={handlePublish}
          disabled={pending}
          className="rounded-full bg-brand-green px-5 py-2 text-sm font-semibold text-brand-off-white disabled:opacity-60"
        >
          {pending ? "Working…" : "Publish to Google"}
        </button>
        <button
          type="button"
          onClick={handleDismiss}
          disabled={pending}
          className="rounded-full border border-brand-black/20 px-5 py-2 text-sm font-semibold text-brand-black/70 disabled:opacity-60"
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
    <p className="mt-0.5 text-sm text-amber-500" aria-label={`${r} out of 5 stars`}>
      {"★".repeat(r)}
      <span className="text-brand-black/20">{"★".repeat(Math.max(0, 5 - r))}</span>
    </p>
  );
}

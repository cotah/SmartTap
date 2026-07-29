"use client";

import { useState, useTransition } from "react";

import {
  approveManualReplyAction,
  generateManualReplyAction,
} from "./actions";

/**
 * Manual fallback while the Google Business API quota is pending: the owner
 * pastes a review, Claude drafts a reply, the owner edits + copies it and
 * pastes it on Google themselves. Copying also saves the pair as an approved
 * example, so future drafts match the owner's tone (few-shot loop).
 */
export function ManualReplyCard() {
  const [comment, setComment] = useState("");
  const [rating, setRating] = useState(5);
  const [author, setAuthor] = useState("");
  const [draft, setDraft] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [pending, startTransition] = useTransition();

  function handleGenerate() {
    setError(null);
    setCopied(false);
    startTransition(async () => {
      const res = await generateManualReplyAction({
        comment,
        rating,
        author: author || null,
      });
      if (res.ok) {
        setDraft(res.draft);
        setReply(res.draft);
      } else {
        setError(res.message);
      }
    });
  }

  function handleCopy() {
    setError(null);
    startTransition(async () => {
      try {
        await navigator.clipboard.writeText(reply.trim());
      } catch {
        setError("Could not access the clipboard — copy the text manually.");
        return;
      }
      const res = await approveManualReplyAction({
        comment,
        rating,
        author: author || null,
        aiDraft: draft,
        replyText: reply,
      });
      if (res.ok) {
        setCopied(true);
      } else {
        // Clipboard already has the text; surface the save failure.
        setError(res.message);
      }
    });
  }

  function handleReset() {
    setComment("");
    setRating(5);
    setAuthor("");
    setDraft(null);
    setReply("");
    setError(null);
    setCopied(false);
  }

  return (
    <div className="rounded-2xl border border-electric-border bg-electric-surface p-4">
      <p className="font-display text-lg">Reply to a review</p>
      <p className="text-sm text-electric-text-muted">
        Paste a Google review, get a suggested reply, copy it and post it on
        Google. Copied replies teach SmartTap your tone.
      </p>

      <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
        Review text
      </label>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={3}
        maxLength={4000}
        className="mt-1 w-full rounded-xl border border-electric-border p-3 text-sm focus:border-electric-cyan focus:outline-none"
        placeholder="Paste the customer's review here…"
      />

      <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
        <div>
          <span className="block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
            Rating
          </span>
          <div className="mt-1 flex gap-1" role="radiogroup" aria-label="Rating">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                role="radio"
                aria-checked={rating === star}
                aria-label={`${star} star${star > 1 ? "s" : ""}`}
                onClick={() => setRating(star)}
                className={`text-2xl leading-none transition-colors ${
                  star <= rating
                    ? "text-electric-cyan"
                    : "text-electric-text-muted"
                }`}
              >
                ★
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1">
          <label className="block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
            Reviewer name (optional)
          </label>
          <input
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            maxLength={200}
            className="mt-1 w-full rounded-xl border border-electric-border p-2.5 text-sm focus:border-electric-cyan focus:outline-none"
            placeholder="e.g. Alex"
          />
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={pending || comment.trim().length === 0}
          className="shrink-0 rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg disabled:opacity-60"
        >
          {pending && draft === null ? "Generating…" : "Generate reply"}
        </button>
      </div>

      {draft !== null ? (
        <div className="mt-4">
          <label className="block text-xs font-semibold uppercase tracking-wide text-electric-text-muted">
            Suggested reply (edit before copying)
          </label>
          <textarea
            value={reply}
            onChange={(e) => setReply(e.target.value)}
            rows={4}
            maxLength={4000}
            className="mt-1 w-full rounded-xl border border-electric-border p-3 text-sm focus:border-electric-cyan focus:outline-none"
          />
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              disabled={pending || reply.trim().length === 0}
              className="rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg disabled:opacity-60"
            >
              {copied ? "Copied ✓" : pending ? "Working…" : "Copy reply"}
            </button>
            {copied ? (
              <button
                type="button"
                onClick={handleReset}
                className="rounded-full border border-electric-border px-5 py-2 text-sm font-semibold text-electric-text-muted"
              >
                Reply to another
              </button>
            ) : null}
          </div>
          {copied ? (
            <p className="mt-2 text-sm text-electric-text-muted">
              Paste it as your reply on Google. Saved as an approved example.
            </p>
          ) : null}
        </div>
      ) : null}

      {error ? <p className="mt-2 text-sm text-red-300">{error}</p> : null}
    </div>
  );
}

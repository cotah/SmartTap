"use client";

import { useState, useTransition } from "react";

import { downloadMonthlyReportAction } from "./actions";

/**
 * Triggers an on-demand monthly PDF download for the authenticated tenant.
 *
 * No date picker for now — the cron-and-dashboard MVP is "give me the
 * previous month right now". When merchants ask for older months we can
 * grow this into a dropdown; the underlying action already takes
 * year/month so it's a UI-only change.
 */
export function MonthlyReportButton() {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function onClick() {
    setError(null);
    startTransition(async () => {
      const result = await downloadMonthlyReportAction();
      if (!result.ok) {
        setError(result.message);
        return;
      }
      // Rebuild the PDF byte-for-byte from base64. atob -> Uint8Array is
      // the standard browser path; Blob lets the same code work in every
      // engine without any base64 polyfill.
      const binary = atob(result.pdfBase64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i += 1) {
        bytes[i] = binary.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = result.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
  }

  return (
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <button
        type="button"
        onClick={onClick}
        disabled={pending}
        className="rounded-lg border border-electric-border bg-electric-surface px-4 py-2.5 text-sm font-medium text-electric-text transition-colors hover:border-electric-cyan hover:text-electric-cyan disabled:opacity-60"
      >
        {pending ? "Preparing…" : "Download monthly PDF"}
      </button>
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}

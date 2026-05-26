"use client";

import { X } from "lucide-react";
import * as React from "react";

import { useMounted } from "@/lib/hooks/use-mounted";
import {
  FOUNDING_SPOTS_REMAINING,
  FOUNDING_TOTAL,
} from "@/lib/landing/constants";
import { cn } from "@/lib/utils";

/**
 * Sticky top banner — the scarcity hook above the hero.
 *
 * Behaviour:
 * - When founding spots > 0: shows "🇮🇪 N founding spots open — stand
 *   free, €29/mo for life" with amber accent on the count.
 * - When founding spots = 0: closes the offer, shows neutral standard-
 *   pricing line, no scarcity, no urgency. Banner stays visible.
 * - User can dismiss; we remember for 7 days via localStorage. Re-shown
 *   after, since the offer is the primary differentiator.
 *
 * Hydration: server renders the banner visible (mounted=false → fall
 * through to default visible state). On mount we check localStorage and
 * potentially hide. Brief visible flash is fine; the alternative (always
 * hidden until JS confirms) trades a flash for the much worse "promo
 * banner pops in 200ms after first paint".
 */
const DISMISS_KEY = "smarttap:landing-banner-dismissed-at";
const DISMISS_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;

export function TopBanner() {
  const mounted = useMounted();
  const [dismissed, setDismissed] = React.useState(false);

  React.useEffect(() => {
    try {
      const raw = window.localStorage.getItem(DISMISS_KEY);
      if (!raw) return;
      const at = Number(raw);
      if (!Number.isFinite(at)) return;
      if (Date.now() - at < DISMISS_WINDOW_MS) {
        setDismissed(true);
      } else {
        window.localStorage.removeItem(DISMISS_KEY);
      }
    } catch {
      // Quota errors, private-mode Safari — ignore, show the banner.
    }
  }, []);

  function dismiss() {
    setDismissed(true);
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      // Same as above — if storage refuses, the banner just won't be
      // remembered. No user-visible failure.
    }
  }

  if (mounted && dismissed) return null;

  const open = FOUNDING_SPOTS_REMAINING > 0;

  return (
    <div
      role="region"
      aria-label="Founding member offer"
      className={cn(
        "relative z-40 w-full border-b border-green-800 bg-green-900 text-cream",
      )}
    >
      <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-4 px-6 py-2.5 text-sm md:px-12 lg:px-16">
        <p className="flex flex-1 items-center justify-center gap-2 text-center leading-snug">
          {open ? (
            <>
              <span aria-hidden="true">🇮🇪</span>
              <span>
                <strong className="font-semibold text-amber-500">
                  {FOUNDING_SPOTS_REMAINING} of {FOUNDING_TOTAL} founding spots
                  open
                </strong>
                <span className="ml-2 hidden text-cream/85 sm:inline">
                  — stand free, €29/mo for life
                </span>
              </span>
            </>
          ) : (
            <span className="text-cream/85">
              Founding offer closed — standard pricing live.
            </span>
          )}
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss banner"
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
            "text-cream/70 transition-colors hover:bg-green-800 hover:text-cream",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500",
          )}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

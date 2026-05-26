"use client";

import dynamic from "next/dynamic";
import * as React from "react";

import {
  BOOK_CALL_MAILTO,
  BOOK_CALL_URL,
} from "@/lib/landing/constants";

import { LandingButton, type LandingButtonProps } from "./button";

/**
 * "15 minutes with the founder" CTA.
 *
 * Two modes driven by `BOOK_CALL_URL` from `lib/landing/constants.ts`:
 *
 * 1. URL set → renders a Radix Dialog with @calcom/embed-react inline.
 *    The Dialog code (and the ~80kB Cal embed it imports) is lazy-loaded
 *    via `next/dynamic` so it never enters the initial / page chunk.
 *
 * 2. URL empty → renders a `mailto:` button. No Dialog, no Cal imports.
 *    This is the pre-launch fallback (LANDING-SPEC.md §5).
 *
 * Both paths produce the same visible button so call sites don't branch.
 */
const BookCallDialog = dynamic(
  () => import("./book-call-dialog").then((mod) => mod.BookCallDialog),
  {
    ssr: false,
    // Static button as the loading state — keeps layout stable, no spinner
    // jitter while Cal loads in the background after first hover/idle.
    loading: () => null,
  },
);

type BookCallButtonProps = Omit<
  Extract<LandingButtonProps, { href?: undefined }>,
  "children" | "href"
> & {
  /** Override the button label. Default: "15 minutes with the founder". */
  label?: string;
};

const DEFAULT_LABEL = "Book 15-min call with Henrique";

export function BookCallButton({
  label = DEFAULT_LABEL,
  variant = "secondary",
  size = "lg",
  className,
  ...rest
}: BookCallButtonProps) {
  if (!BOOK_CALL_URL) {
    return (
      <LandingButton
        href={`mailto:${BOOK_CALL_MAILTO}?subject=${encodeURIComponent(
          "15-min call about SmartTap",
        )}&body=${encodeURIComponent(
          "Hi Henrique,\n\nI'd like to book a 15-min call about SmartTap for my shop.\n\nName:\nShop:\nBest time:\n",
        )}`}
        external
        variant={variant}
        size={size}
        className={className}
      >
        {label}
      </LandingButton>
    );
  }

  return (
    <BookCallDialog
      label={label}
      variant={variant}
      size={size}
      className={className}
      {...rest}
    />
  );
}

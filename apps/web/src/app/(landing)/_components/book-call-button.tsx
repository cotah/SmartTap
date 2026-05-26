"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Cal, { getCalApi } from "@calcom/embed-react";
import { X } from "lucide-react";
import * as React from "react";

import {
  BOOK_CALL_MAILTO,
  BOOK_CALL_URL,
} from "@/lib/landing/constants";
import { cn } from "@/lib/utils";

import { LandingButton, type LandingButtonProps } from "./button";

/**
 * "15 minutes with the founder" CTA.
 *
 * Two modes driven by `BOOK_CALL_URL` from `lib/landing/constants.ts`:
 *
 * 1. If `BOOK_CALL_URL` is set (Cal.com username/event-type) → opens a
 *    Radix Dialog with @calcom/embed-react inline. No third-party
 *    redirect. The Cal API auto-handles ARIA + focus inside the iframe.
 *
 * 2. If empty → renders as a `mailto:` button. No Dialog at all, just a
 *    direct link that pops the user's mail client with prefilled subject.
 *    This is the fallback Henrique uses pre-launch until Cal.com is
 *    wired (see LANDING-SPEC.md §5).
 *
 * Both paths produce the same visible button so call sites don't branch.
 */
type BookCallButtonProps = Omit<
  Extract<LandingButtonProps, { href?: undefined }>,
  "children" | "href"
> & {
  /** Override the button label. Default: "15 minutes with the founder". */
  label?: string;
  /** PostHog/analytics hint sent to the parent click handler if any. Not
   * used for now — slot for Phase 6 analytics wiring. */
  location?: string;
};

const DEFAULT_LABEL = "15 minutes with the founder";

export function BookCallButton({
  label = DEFAULT_LABEL,
  variant = "secondary",
  size = "lg",
  className,
  ...rest
}: BookCallButtonProps) {
  // No Cal.com URL → render as plain mailto. Simple, no Dialog overhead.
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

  return <BookCallDialog label={label} variant={variant} size={size} className={className} {...rest} />;
}

/**
 * Cal.com embed inside a Radix Dialog. Only mounted when the user opens
 * the dialog — saves the ~80kB Cal.com bundle from blocking first paint.
 */
function BookCallDialog({
  label,
  variant,
  size,
  className,
  ...rest
}: BookCallButtonProps & { label: string }) {
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    (async () => {
      const cal = await getCalApi({ namespace: "founder15" });
      cal("ui", {
        // Lock theme to brand cream + green per LANDING-SPEC.md §4. Cal
        // exposes only `light`/`dark` so we accept light and override via
        // styles below if needed.
        theme: "light",
        cssVarsPerTheme: {
          light: {
            "cal-brand": "#1B4D3E",
            "cal-text": "#1A1A1A",
            "cal-bg": "#F7F5F0",
          },
          // Cal requires the dark key even when we lock theme to light.
          // Mirror the same brand tokens so embeds inside an OS dark-mode
          // browser don't fall back to the default Cal palette.
          dark: {
            "cal-brand": "#E8A020",
            "cal-text": "#F7F5F0",
            "cal-bg": "#1A1A1A",
          },
        },
        hideEventTypeDetails: false,
        layout: "month_view",
      });
    })();
  }, [open]);

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <LandingButton variant={variant} size={size} className={className} {...rest}>
          {label}
        </LandingButton>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            "fixed inset-0 z-50 bg-neutral-900/60 backdrop-blur-sm",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0",
          )}
        />
        <Dialog.Content
          aria-describedby={undefined}
          className={cn(
            "fixed left-1/2 top-1/2 z-50 w-[min(960px,92vw)] -translate-x-1/2 -translate-y-1/2",
            "rounded-2xl border border-neutral-300 bg-cream shadow-2xl",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
          )}
        >
          <div className="flex items-center justify-between border-b border-neutral-300 px-6 py-4">
            <Dialog.Title className="font-display text-2xl leading-tight tracking-tight">
              Book a 15-min call
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close"
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-md text-neutral-600",
                  "transition-colors hover:bg-neutral-300/40 hover:text-neutral-900",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500",
                )}
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </Dialog.Close>
          </div>
          <div className="max-h-[80vh] overflow-y-auto">
            <Cal
              namespace="founder15"
              calLink={BOOK_CALL_URL}
              style={{ width: "100%", height: "640px", overflow: "auto" }}
              config={{ layout: "month_view" }}
            />
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

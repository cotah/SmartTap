"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Cal, { getCalApi } from "@calcom/embed-react";
import { X } from "lucide-react";
import * as React from "react";

import { BOOK_CALL_URL } from "@/lib/landing/constants";
import { cn } from "@/lib/utils";

import { LandingButton, type LandingButtonProps } from "./button";

/**
 * Cal.com booking inside a Radix Dialog.
 *
 * Lives in its own file so the parent (`BookCallButton`) can lazy-load
 * it via `next/dynamic` — keeping the ~80kB Cal embed out of the
 * initial page chunk. Only rendered when `BOOK_CALL_URL` is non-empty.
 */
type Props = Omit<
  Extract<LandingButtonProps, { href?: undefined }>,
  "children" | "href"
> & {
  label: string;
};

export function BookCallDialog({
  label,
  variant = "secondary",
  size = "lg",
  className,
  ...rest
}: Props) {
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    if (!open) return;
    (async () => {
      const cal = await getCalApi({ namespace: "founder15" });
      cal("ui", {
        theme: "light",
        cssVarsPerTheme: {
          // Lock the booking UI to the SmartTap brand palette in both
          // light and dark schemes so the embed never falls back to the
          // default purple Cal accent.
          light: {
            "cal-brand": "#1B4D3E",
            "cal-text": "#1A1A1A",
            "cal-bg": "#F7F5F0",
          },
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
        <LandingButton
          variant={variant}
          size={size}
          className={className}
          {...rest}
        >
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

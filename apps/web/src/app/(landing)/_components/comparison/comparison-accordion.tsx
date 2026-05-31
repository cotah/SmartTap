"use client";

import * as Accordion from "@radix-ui/react-accordion";
import { Check, ChevronDown, X } from "lucide-react";
import * as React from "react";

import { COMPARISON_ROWS } from "@/lib/landing/comparison-data";
import { cn } from "@/lib/utils";

/**
 * Mobile comparison view — Radix Accordion. Each axis is collapsible so
 * the section doesn't dominate the small-screen scroll.
 *
 * First item open by default to demonstrate the format. Tap the chevron
 * (or anywhere on the trigger) to reveal SmartTap vs alternatives for
 * that axis. Radix handles all the ARIA + keyboard semantics.
 */
export function ComparisonAccordion() {
  return (
    <div className="md:hidden">
      <Accordion.Root
        type="single"
        collapsible
        defaultValue={COMPARISON_ROWS[0]?.axis}
        className="overflow-hidden rounded-2xl border border-electric-border bg-electric-surface"
      >
        {COMPARISON_ROWS.map((row, i) => (
          <Accordion.Item
            key={row.axis}
            value={row.axis}
            className={cn(
              i !== COMPARISON_ROWS.length - 1 && "border-b border-electric-border",
            )}
          >
            <Accordion.Trigger
              className={cn(
                "group flex w-full items-center justify-between px-5 py-4 text-left",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-electric-cyan",
              )}
            >
              <span className="text-base font-medium text-electric-text">
                {row.axis}
              </span>
              <ChevronDown
                className="h-4 w-4 shrink-0 text-electric-text-muted transition-transform duration-300 group-data-[state=open]:rotate-180"
                aria-hidden="true"
              />
            </Accordion.Trigger>
            <Accordion.Content
              className={cn(
                "overflow-hidden text-sm",
                "data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up",
              )}
            >
              <div className="grid gap-3 px-5 pb-5 pt-1">
                <Row label="SmartTap" value={row.smarttap} win />
                <Row label="Typical alternatives" value={row.others} />
              </div>
            </Accordion.Content>
          </Accordion.Item>
        ))}
      </Accordion.Root>
    </div>
  );
}

function Row({
  label,
  value,
  win,
}: {
  label: string;
  value: string;
  win?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg px-3 py-3",
        win ? "bg-electric-cyan/[0.06]" : "bg-transparent",
      )}
    >
      {win ? (
        <Check className="mt-0.5 h-4 w-4 shrink-0 text-electric-cyan" aria-hidden="true" />
      ) : (
        <X className="mt-0.5 h-4 w-4 shrink-0 text-electric-text-muted" aria-hidden="true" />
      )}
      <div className="flex flex-1 flex-col">
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-electric-text-muted">
          {label}
        </span>
        <span className={cn("mt-0.5 text-sm", win ? "text-electric-text" : "text-electric-text-muted")}>
          {value}
        </span>
      </div>
    </div>
  );
}

"use client";

import * as Accordion from "@radix-ui/react-accordion";
import { Plus } from "lucide-react";
import * as React from "react";

import { FAQ_ITEMS } from "@/lib/landing/faq-data";
import { cn } from "@/lib/utils";

import { Section, SectionEyebrow } from "../section";

/**
 * Section 7 — FAQ. 8 questions per LANDING-SPEC §3, ordered to pre-empt
 * the doubts a skeptical owner has BEFORE they ask: app? phones? data?
 * cancel? GDPR? setup fee?
 *
 * Built on Radix Accordion (same keyframes as the comparison accordion).
 * No default-open item — each opens on user intent. Plus icon rotates
 * 45° to become X when expanded, communicating the toggle affordance
 * without needing a separate close button.
 *
 * Narrow container (max-w-680) gives the long-form answers a readable
 * line length.
 */
export function Faq() {
  return (
    <Section id="faq" containerSize="narrow">
      <header className="mb-10 flex flex-col items-start gap-4 md:mb-12">
        <SectionEyebrow>Common questions</SectionEyebrow>
        <h2 className="font-display text-3xl font-semibold leading-tight tracking-[-0.02em] text-electric-text md:text-[44px]">
          Everything an owner asks before signing.
        </h2>
      </header>

      <Accordion.Root type="single" collapsible className="flex flex-col">
        {FAQ_ITEMS.map((item, i) => (
          <Accordion.Item
            key={item.q}
            value={item.q}
            className={cn(
              "border-b border-electric-border",
              i === 0 && "border-t",
            )}
          >
            <Accordion.Header>
              <Accordion.Trigger
                className={cn(
                  "group flex w-full items-center justify-between gap-6 py-5 text-left md:py-6",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-electric-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-electric-bg",
                )}
              >
                <span className="font-display text-lg font-semibold leading-snug tracking-tight text-electric-text md:text-xl">
                  {item.q}
                </span>
                <Plus
                  className={cn(
                    "h-5 w-5 shrink-0 text-electric-cyan transition-transform duration-300",
                    "group-data-[state=open]:rotate-45",
                  )}
                  aria-hidden="true"
                />
              </Accordion.Trigger>
            </Accordion.Header>
            <Accordion.Content
              className={cn(
                "overflow-hidden",
                "data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up",
              )}
            >
              <p className="pb-6 pr-12 text-base leading-relaxed text-electric-text-muted md:text-[17px]">
                {item.a}
              </p>
            </Accordion.Content>
          </Accordion.Item>
        ))}
      </Accordion.Root>
    </Section>
  );
}

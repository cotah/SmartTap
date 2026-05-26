"use client";

import * as React from "react";

import { ScrollFade } from "../scroll-fade";

/**
 * Single step card for "How it works" (Section 3).
 *
 * Visual: mono step number top-left (01/02/03), then icon, then title +
 * body. The icon is a single amber stroke — the only amber on the card,
 * keeping with the 5% rule. Background is cream-over-cream with a thin
 * neutral border so cards feel structural rather than floating.
 *
 * `delay` drives the IntersectionObserver-based stagger — 0 for the
 * first card, 0.08s for the second, 0.16s for the third.
 */
type StepCardProps = {
  number: string;
  title: string;
  body: string;
  icon: React.ReactNode;
  delay?: number;
};

export function StepCard({ number, title, body, icon, delay = 0 }: StepCardProps) {
  return (
    <ScrollFade delay={delay} className="h-full">
      <article className="flex h-full flex-col gap-5 rounded-2xl border border-neutral-300/80 bg-cream/70 p-7 md:p-8">
        <header className="flex items-start justify-between">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-neutral-600">
            {number}
          </p>
          <span aria-hidden="true" className="text-amber-500">
            {icon}
          </span>
        </header>
        <h3 className="font-display text-2xl leading-snug tracking-tight text-neutral-900 md:text-[26px]">
          {title}
        </h3>
        <p className="text-base leading-relaxed text-neutral-600">{body}</p>
      </article>
    </ScrollFade>
  );
}

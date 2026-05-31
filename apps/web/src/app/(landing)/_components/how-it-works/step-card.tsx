"use client";

import * as React from "react";

import { ScrollFade } from "../scroll-fade";

/**
 * Single step card for "How it works" (Section 3).
 *
 * Visual: mono step number top-left (01/02/03), then icon, then title +
 * body. The icon is a single cyan stroke. Background is a raised dark
 * surface with a thin border so cards feel structural rather than floating.
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
      <article className="flex h-full flex-col gap-5 rounded-2xl border border-electric-border bg-electric-surface p-7 transition-colors duration-200 hover:border-electric-cyan/40 md:p-8">
        <header className="flex items-start justify-between">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-electric-text-muted">
            {number}
          </p>
          <span
            aria-hidden="true"
            className="text-electric-cyan [filter:drop-shadow(0_0_8px_rgba(0,212,255,0.5))]"
          >
            {icon}
          </span>
        </header>
        <h3 className="font-display text-2xl font-semibold leading-snug tracking-tight text-electric-text md:text-[26px]">
          {title}
        </h3>
        <p className="text-base leading-relaxed text-electric-text-muted">{body}</p>
      </article>
    </ScrollFade>
  );
}

"use client";

import * as React from "react";

import { ScrollFade } from "../scroll-fade";

/**
 * Single problem card. Visually quieter than step cards — these are the
 * "ouch, that's me" moments, so we don't want to glamourize them. No
 * border, no icon: just a mono number and the owner's-voice line in
 * neutral-900 body.
 */
export function ProblemCard({
  number,
  text,
  delay = 0,
}: {
  number: string;
  text: string;
  delay?: number;
}) {
  return (
    <ScrollFade delay={delay} className="h-full">
      <div className="flex h-full flex-col gap-4 py-2">
        <p className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-electric-cyan">
          {number}
        </p>
        <p className="font-display text-2xl font-semibold leading-snug tracking-tight text-electric-text md:text-[28px]">
          {text}
        </p>
      </div>
    </ScrollFade>
  );
}

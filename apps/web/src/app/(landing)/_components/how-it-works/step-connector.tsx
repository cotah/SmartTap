"use client";

import { motion } from "framer-motion";
import * as React from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";

/**
 * Circuit-board connector behind the three "How it works" cards — a thin
 * trace with a cyan pulse travelling tap → review → return, evoking the
 * data flowing through the loop. Inspired by the circuit-board reference,
 * built as a self-contained decorative layer.
 *
 * Desktop only (the cards stack on mobile, so a horizontal trace makes no
 * sense there). Sits behind the cards (-z-10); the opaque card surfaces let
 * it read only in the gaps between them. Reduced motion: static trace, no
 * travelling pulse.
 */
export function StepConnector() {
  const reduced = useReducedMotion();

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-[16%] top-1/2 -z-10 hidden -translate-y-1/2 md:block"
    >
      <div className="relative h-px w-full bg-gradient-to-r from-transparent via-electric-border to-transparent">
        {/* Nodes at the three card centres */}
        {[0, 50, 100].map((left) => (
          <span
            key={left}
            className="absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full border border-electric-border bg-electric-bg"
            style={{ left: `${left}%` }}
          />
        ))}
        {/* Travelling cyan pulse */}
        {!reduced && (
          <motion.span
            className="absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-electric-cyan shadow-[0_0_12px_rgba(0,212,255,0.9)]"
            initial={{ left: "0%" }}
            animate={{ left: ["0%", "100%"] }}
            transition={{
              duration: 3.2,
              repeat: Infinity,
              ease: "easeInOut",
              repeatDelay: 0.6,
            }}
          />
        )}
      </div>
    </div>
  );
}

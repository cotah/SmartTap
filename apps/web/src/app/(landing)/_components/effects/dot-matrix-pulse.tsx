"use client";

import { motion } from "framer-motion";
import * as React from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

/**
 * Dot-matrix NFC pulse — concentric rings of cyan dots that emanate outward
 * in a repeating wave, evoking an NFC tap field. Inspired by the dotmatrix
 * loader set; built from scratch as a self-contained SVG so it carries no
 * external dependency.
 *
 * Reduced motion: renders the rings static and dim (no animation).
 *
 * Sized by the `size` prop (px square). Decorative only — aria-hidden.
 */
const RINGS = [
  { radius: 0, count: 1 },
  { radius: 14, count: 6 },
  { radius: 28, count: 12 },
  { radius: 42, count: 18 },
];

export function DotMatrixPulse({
  size = 120,
  className,
}: {
  size?: number;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const c = size / 2;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      aria-hidden="true"
      className={cn("overflow-visible", className)}
    >
      {RINGS.map((ring, ringIndex) => {
        const dots =
          ring.count === 1
            ? [{ x: c, y: c }]
            : Array.from({ length: ring.count }, (_, i) => {
                const angle = (i / ring.count) * Math.PI * 2;
                return {
                  x: c + Math.cos(angle) * ring.radius,
                  y: c + Math.sin(angle) * ring.radius,
                };
              });

        return dots.map((dot, i) => {
          const baseOpacity = 0.5 - ringIndex * 0.1;
          if (reduced) {
            return (
              <circle
                key={`${ringIndex}-${i}`}
                cx={dot.x}
                cy={dot.y}
                r={1.6}
                fill="#00D4FF"
                opacity={Math.max(0.15, baseOpacity)}
              />
            );
          }
          return (
            <motion.circle
              key={`${ringIndex}-${i}`}
              cx={dot.x}
              cy={dot.y}
              r={1.6}
              fill="#00D4FF"
              initial={{ opacity: 0.12, scale: 0.8 }}
              animate={{ opacity: [0.12, 0.95, 0.12], scale: [0.8, 1.15, 0.8] }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
                // Wave outward: outer rings fire after inner ones.
                delay: ringIndex * 0.22,
              }}
            />
          );
        });
      })}
    </svg>
  );
}

import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Inline SVG mark for SmartTap — the "ST" monogram with NFC waves.
 *
 * Kept inline (not an <img>) so it never adds a network request and the
 * wordmark can inherit colour from the wrapper. The wave arcs imply NFC tap
 * radius without literal radio glyphs — quieter than the official tap icon,
 * and lets the mark scale down to favicon size without losing identity.
 *
 * Two variants (rebrand 2026-05-31):
 *  - `electric` (Dark Electric): cyan plate + near-black monogram/waves +
 *    white wordmark. Mirrors the CTA (cyan fill, black text). Used on the
 *    dark landing.
 *  - `classic` (legacy): green plate + amber monogram. Used on surfaces not
 *    yet migrated (dashboard, etc). Default until the rest of the product
 *    cascades to Dark Electric.
 *
 * Default size 32px (header). Footer uses 40px. OG image uses 96px.
 */
export function BrandLogo({
  className,
  size = 32,
  withWordmark = false,
  title = "SmartTap",
  variant = "classic",
}: {
  className?: string;
  size?: number;
  withWordmark?: boolean;
  title?: string;
  variant?: "classic" | "electric";
}) {
  const electric = variant === "electric";
  const plate = electric ? "#00D4FF" : "currentColor";
  const ink = electric ? "#0A0A0F" : "#E8A020";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2",
        electric ? "text-electric-text" : "text-green-900",
        className,
      )}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label={title}
      >
        <title>{title}</title>
        {/* Rounded square plate */}
        <rect width="40" height="40" rx="9" fill={plate} />
        {/* "ST" monogram, optical-centered */}
        <path
          d="M11.8 14.3c0-1.45 1.18-2.6 2.6-2.6h3.4c1.45 0 2.6 1.18 2.6 2.6 0 .55-.18 1.05-.5 1.45-.32.4-.78.65-1.3.7H14.4c-.05 0-.1.05-.1.1v.5c0 .05.05.1.1.1h3.7c1.55.05 2.85 1.3 2.95 2.85.1 1.7-1.25 3.1-2.95 3.1H11.8a.7.7 0 01-.7-.7v-1.4c0-.4.3-.7.7-.7h6.3c.45 0 .8-.35.8-.8s-.35-.8-.8-.8h-3.5c-1.6 0-2.95-1.2-3.05-2.8-.1-.55-.05-1 .25-1.6z"
          fill={ink}
        />
        <path
          d="M22.1 11.7c-.4 0-.7.3-.7.7v1.4c0 .4.3.7.7.7h2.05v8.4c0 .4.3.7.7.7h1.4c.4 0 .7-.3.7-.7v-8.4h2.05c.4 0 .7-.3.7-.7v-1.4c0-.4-.3-.7-.7-.7H22.1z"
          fill={ink}
        />
        {/* NFC wave arcs — top-right corner, decorative */}
        <path
          d="M30 8.5c1.5 1.5 1.5 4 0 5.5"
          stroke={ink}
          strokeWidth="1.2"
          strokeLinecap="round"
          opacity="0.7"
        />
        <path
          d="M32 6.5c2.5 2.5 2.5 7 0 9.5"
          stroke={ink}
          strokeWidth="1.2"
          strokeLinecap="round"
          opacity="0.45"
        />
      </svg>
      {withWordmark && (
        <span className="font-display text-xl leading-none tracking-tight">
          SmartTap
        </span>
      )}
    </span>
  );
}

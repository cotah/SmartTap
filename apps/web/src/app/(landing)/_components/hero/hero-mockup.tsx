"use client";

import { motion } from "framer-motion";
import * as React from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";

import { DotMatrixPulse } from "../effects/dot-matrix-pulse";
import { ParallaxLayer, ShowcaseCard } from "../effects/showcase-card";

/**
 * Hero visual — Dark Electric.
 *
 * A crafted 3D-style render of the SmartTap counter stand in matte black
 * with electric-cyan branding, floated inside a Showcase Card (3D tilt +
 * parallax) with a cyan glow. The NFC tap field is the animated dot-matrix
 * pulse over the tap zone.
 *
 * PLACEHOLDER: this crafted SVG stands in until a real photo of the
 * black+cyan reprinted stand exists. When it lands, swap the <svg> for a
 * <ParallaxLayer><Image src="/stand-render.jpg" .../></ParallaxLayer>
 * (the Showcase Card + glow + pulse stay).
 */
export function HeroMockup() {
  const reduced = useReducedMotion();

  return (
    <motion.div
      className="relative aspect-[5/4] w-full"
      initial={reduced ? false : { opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
    >
      <ShowcaseCard className="h-full w-full">
        <div className="relative aspect-[5/4] w-full p-6">
          <ParallaxLayer className="h-full w-full">
            <svg
              viewBox="0 0 440 360"
              className="h-full w-full"
              xmlns="http://www.w3.org/2000/svg"
              role="img"
              aria-label="SmartTap NFC counter stand in matte black with electric-cyan branding"
            >
              <title>SmartTap counter stand — Dark Electric</title>

              {/* Floor reflection — cyan-tinted glow pooled under the stand */}
              <ellipse cx="220" cy="318" rx="120" ry="14" fill="url(#floorGlow)" />

              {/* Stand base / foot — gives the upright face something to sit on */}
              <path
                d="M150 300 L290 300 L300 322 L140 322 Z"
                fill="#0E0E15"
                stroke="#1A2A3A"
                strokeWidth="1"
              />

              {/* Upright tap face — the body of the stand */}
              <rect
                x="150"
                y="64"
                width="140"
                height="240"
                rx="18"
                fill="url(#bodyGradient)"
                stroke="#1A2A3A"
                strokeWidth="1.5"
              />
              {/* Left edge cyan rim light for depth */}
              <rect x="150" y="64" width="4" height="240" rx="2" fill="#00D4FF" opacity="0.5" />
              {/* Top bevel highlight */}
              <rect x="150" y="64" width="140" height="6" rx="3" fill="#00BFEA" opacity="0.35" />

              {/* Logo plate — cyan rounded square with dark ST monogram */}
              <g transform="translate(186 104)">
                <rect width="68" height="68" rx="16" fill="#00D4FF" />
                <rect width="68" height="68" rx="16" fill="url(#plateSheen)" opacity="0.5" />
                <text
                  x="34"
                  y="48"
                  textAnchor="middle"
                  fontFamily="var(--font-geist-sans), system-ui, sans-serif"
                  fontSize="38"
                  fontWeight="700"
                  fill="#0A0A0F"
                >
                  ST
                </text>
              </g>

              {/* "TAP TO REVIEW" label */}
              <text
                x="220"
                y="214"
                textAnchor="middle"
                fontFamily="var(--font-geist-mono), monospace"
                fontSize="12"
                letterSpacing="2"
                fill="#8899AA"
              >
                TAP TO REVIEW
              </text>

              {/* Subtle NFC tag glyph hint near the bottom of the face */}
              <rect
                x="196"
                y="244"
                width="48"
                height="32"
                rx="6"
                fill="none"
                stroke="#1A2A3A"
                strokeWidth="1.5"
              />
              <circle cx="220" cy="260" r="5" fill="none" stroke="#00D4FF" strokeWidth="1.5" opacity="0.7" />

              <defs>
                <linearGradient id="bodyGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#1A1A24" />
                  <stop offset="1" stopColor="#0A0A0F" />
                </linearGradient>
                <linearGradient id="plateSheen" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.4" />
                  <stop offset="0.5" stopColor="#FFFFFF" stopOpacity="0" />
                </linearGradient>
                <radialGradient id="floorGlow" cx="0.5" cy="0.5" r="0.5">
                  <stop offset="0" stopColor="#00D4FF" stopOpacity="0.35" />
                  <stop offset="1" stopColor="#00D4FF" stopOpacity="0" />
                </radialGradient>
              </defs>
            </svg>
          </ParallaxLayer>

          {/* NFC pulse field — centered over the logo / tap zone */}
          <div className="pointer-events-none absolute left-1/2 top-[38%] -translate-x-1/2 -translate-y-1/2">
            <DotMatrixPulse size={150} />
          </div>
        </div>
      </ShowcaseCard>
    </motion.div>
  );
}

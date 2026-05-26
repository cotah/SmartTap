"use client";

import { motion } from "framer-motion";
import * as React from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";

/**
 * Hero visual — placeholder SVG illustration of the SmartTap stand on a
 * café counter.
 *
 * Replaced with a real iPhone photo by build day per LANDING-SPEC.md C1.
 * When the photo lands, swap this whole component for:
 *     <Image src="/hero-stand.jpg" alt="..." priority width={...} height={...} />
 *
 * For now the illustration carries the visual weight: warm wood counter
 * tone, the stand in green with a subtle amber NFC glow, and a coffee
 * cup for context. Stays neutral about which Dublin shop it is — generic
 * enough that any barbershop / café owner can project themselves into it.
 *
 * Parallax effect (0.15× scroll rate per LANDING-SPEC §4) is opt-in via
 * framer-motion `useScroll`. Off on reduced-motion.
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
      {/* Soft ambient blob behind the stand — gives the illustration depth
       * without a hard drop shadow that fights the cream background. */}
      <div
        aria-hidden="true"
        className="absolute inset-x-8 inset-y-12 -z-10 rounded-[40%] bg-amber-50 opacity-70 blur-2xl"
      />

      <svg
        viewBox="0 0 500 400"
        className="h-full w-full"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-label="SmartTap NFC stand on a counter, next to a coffee cup"
      >
        <title>SmartTap stand on a Dublin café counter</title>

        {/* Counter — warm oak tone, two layers for the bevel */}
        <rect x="0" y="290" width="500" height="110" fill="#D6BFA0" />
        <rect x="0" y="290" width="500" height="14" fill="#B89A77" />
        {/* Subtle grain lines */}
        <g stroke="#B89A77" strokeWidth="0.5" opacity="0.45">
          <line x1="0" y1="320" x2="500" y2="320" />
          <line x1="0" y1="345" x2="500" y2="345" />
          <line x1="0" y1="370" x2="500" y2="370" />
        </g>

        {/* Stand shadow on counter */}
        <ellipse cx="220" cy="298" rx="90" ry="6" fill="#1A1A1A" opacity="0.18" />
        {/* Cup shadow */}
        <ellipse cx="380" cy="298" rx="48" ry="4" fill="#1A1A1A" opacity="0.18" />

        {/* === Stand body (counter stand format, ~80x80x60mm) === */}
        {/* Base */}
        <rect x="160" y="240" width="130" height="56" rx="6" fill="#1B4D3E" />
        <rect x="160" y="240" width="130" height="10" rx="6" fill="#245C4B" />
        {/* Vertical face — the NFC tap zone */}
        <path d="M170 240 L170 100 Q170 90 180 90 L260 90 Q280 90 280 110 L280 240 Z" fill="#1B4D3E" />
        <path d="M170 240 L170 100 Q170 90 180 90 L260 90 Q280 90 280 110 L280 240 Z" fill="url(#standGradient)" opacity="0.55" />

        {/* Brand mark on stand */}
        <g transform="translate(192 130)">
          <rect width="60" height="60" rx="14" fill="#F7F5F0" />
          <text x="30" y="42" textAnchor="middle" fontFamily="serif" fontSize="34" fontWeight="400" fill="#1B4D3E">ST</text>
        </g>
        <text x="225" y="218" textAnchor="middle" fontFamily="sans-serif" fontSize="11" fill="#F7F5F0" letterSpacing="1.2">TAP TO REVIEW</text>
        {/* NFC waves above the brand mark */}
        <g stroke="#E8A020" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.85">
          {!reduced ? (
            <>
              <motion.path
                d="M225 108 Q225 102 218 102"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
              />
              <motion.path
                d="M225 108 Q225 96 213 96"
                animate={{ opacity: [0.2, 0.8, 0.2] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut", delay: 0.2 }}
              />
              <motion.path
                d="M225 108 Q225 90 208 90"
                animate={{ opacity: [0.1, 0.6, 0.1] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
              />
            </>
          ) : (
            <>
              <path d="M225 108 Q225 102 218 102" opacity="0.6" />
              <path d="M225 108 Q225 96 213 96" opacity="0.4" />
              <path d="M225 108 Q225 90 208 90" opacity="0.25" />
            </>
          )}
        </g>

        {/* === Coffee cup === */}
        <g transform="translate(340 195)">
          <ellipse cx="40" cy="6" rx="40" ry="6" fill="#F7F5F0" />
          <path d="M0 6 L6 95 Q6 100 11 100 L69 100 Q74 100 74 95 L80 6 Z" fill="#F7F5F0" />
          <path d="M6 6 L74 6 L72 22 L8 22 Z" fill="#1A1A1A" opacity="0.06" />
          {/* Coffee surface */}
          <ellipse cx="40" cy="6" rx="36" ry="4" fill="#5C3A21" />
          {/* Handle */}
          <path d="M76 30 Q98 30 98 55 Q98 80 76 80" stroke="#F7F5F0" strokeWidth="6" fill="none" />
          {/* Steam */}
          {!reduced && (
            <>
              <motion.path
                d="M25 -6 Q22 -16 28 -22 Q34 -28 30 -38"
                stroke="#D8D5CD"
                strokeWidth="2"
                strokeLinecap="round"
                fill="none"
                animate={{ opacity: [0.3, 0.7, 0.3], y: [0, -4, 0] }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              />
              <motion.path
                d="M50 -8 Q47 -18 53 -24 Q59 -30 55 -40"
                stroke="#D8D5CD"
                strokeWidth="2"
                strokeLinecap="round"
                fill="none"
                animate={{ opacity: [0.3, 0.7, 0.3], y: [0, -4, 0] }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
              />
            </>
          )}
        </g>

        <defs>
          <linearGradient id="standGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#245C4B" stopOpacity="0.5" />
            <stop offset="1" stopColor="#0E2D24" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>

      {/* Tag overlay — "Photo coming soon" hint, removed when real photo lands. */}
      <p className="absolute bottom-3 right-3 rounded-full bg-cream/90 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-neutral-600 shadow-sm">
        photo soon · illustration for now
      </p>
    </motion.div>
  );
}

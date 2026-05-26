"use client";

import { motion, type Transition } from "framer-motion";
import * as React from "react";

/**
 * Inline SVG primitives for the animated demo timeline.
 *
 * Each shape exports a `motion.*` element keyed to the parent demo's
 * 4.5-second cycle. Times below are normalized [0..1] against 4.5s so
 * the timeline math stays readable.
 *
 * Stages:
 *   0.00–0.18  stand fades in, amber glow starts pulsing
 *   0.18–0.36  phone slides in from right
 *   0.36–0.53  tap ripple expands from contact point
 *   0.53–0.76  stars fill left→right, "submitted" slides up
 *   0.76–1.00  hold, fade out, ready to restart
 *
 * The looped cycle is driven from `AnimatedDemo` via `repeat: Infinity` +
 * `repeatDelay: 0.8` on each child, so motion stays in sync without a
 * single orchestrator state (which would re-render every frame).
 */
const CYCLE_S = 4.5;

/** Build a framer-motion transition with the standard cycle settings. */
function cycleTransition(): Transition {
  return {
    duration: CYCLE_S,
    repeat: Infinity,
    repeatDelay: 0.8,
    ease: "linear",
    // Each motion element supplies its own `times` array so values change
    // at the right beat — see usage below.
  };
}

/** Stand visual — appears at 0.0s, holds until end of cycle. */
export function MotionStand({ playing }: { playing: boolean }) {
  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={
        playing
          ? { opacity: [0, 1, 1, 1, 1, 0] }
          : { opacity: 1 }
      }
      transition={
        playing
          ? { ...cycleTransition(), times: [0, 0.18, 0.36, 0.76, 0.9, 1] }
          : { duration: 0 }
      }
    >
      {/* Stand base + tap face */}
      <rect x="80" y="240" width="120" height="40" rx="6" fill="#1B4D3E" />
      <path
        d="M88 240 L88 80 Q88 70 98 70 L180 70 Q200 70 200 90 L200 240 Z"
        fill="#1B4D3E"
      />
      <path
        d="M88 240 L88 80 Q88 70 98 70 L180 70 Q200 70 200 90 L200 240 Z"
        fill="url(#standFaceGrad)"
        opacity="0.55"
      />
      {/* "ST" mark on stand */}
      <rect x="108" y="120" width="64" height="64" rx="14" fill="#F7F5F0" />
      <text
        x="140"
        y="166"
        textAnchor="middle"
        fontFamily="serif"
        fontSize="36"
        fill="#1B4D3E"
      >
        ST
      </text>
      <text
        x="140"
        y="210"
        textAnchor="middle"
        fontFamily="sans-serif"
        fontSize="10"
        letterSpacing="1.2"
        fill="#F7F5F0"
      >
        TAP TO REVIEW
      </text>

      {/* Amber pulse glow on the tap zone */}
      <motion.circle
        cx="140"
        cy="100"
        r="22"
        fill="#E8A020"
        animate={
          playing
            ? { opacity: [0, 0.65, 0.25, 0.65, 0.25, 0] }
            : { opacity: 0 }
        }
        transition={
          playing
            ? { ...cycleTransition(), times: [0, 0.1, 0.18, 0.26, 0.36, 0.42] }
            : { duration: 0 }
        }
      />
    </motion.g>
  );
}

/** Phone slides in from right at 0.18s, exits at 0.85s. */
export function MotionPhone({ playing }: { playing: boolean }) {
  return (
    <motion.g
      initial={{ x: 250, opacity: 0 }}
      animate={
        playing
          ? { x: [250, 250, 0, 0, 0, 80], opacity: [0, 0, 1, 1, 1, 0] }
          : { x: 0, opacity: 1 }
      }
      transition={
        playing
          ? {
              ...cycleTransition(),
              ease: ["linear", [0.16, 1, 0.3, 1], "linear", "linear", "linear"],
              times: [0, 0.18, 0.36, 0.76, 0.85, 1],
            }
          : { duration: 0 }
      }
    >
      {/* Phone body */}
      <rect x="240" y="60" width="200" height="280" rx="28" fill="#1A1A1A" />
      <rect x="248" y="68" width="184" height="264" rx="20" fill="#F7F5F0" />

      {/* Status bar */}
      <rect x="262" y="78" width="40" height="4" rx="2" fill="#1A1A1A" opacity="0.2" />
      <rect x="402" y="78" width="20" height="4" rx="2" fill="#1A1A1A" opacity="0.2" />

      {/* In-phone view: shop name + stamp card */}
      <text
        x="340"
        y="115"
        textAnchor="middle"
        fontFamily="serif"
        fontSize="18"
        fill="#1B4D3E"
      >
        Brian&apos;s Barbers
      </text>
      <text
        x="340"
        y="135"
        textAnchor="middle"
        fontFamily="sans-serif"
        fontSize="10"
        fill="#5A5A5A"
      >
        Welcome back, Aoife
      </text>

      {/* Stamp grid — 2 rows × 5 columns */}
      <g transform="translate(258 152)">
        {Array.from({ length: 10 }).map((_, i) => {
          const x = (i % 5) * 33;
          const y = Math.floor(i / 5) * 33;
          // First 6 stamps filled in green, last 4 outlined neutral
          const filled = i < 6;
          return (
            <g key={i} transform={`translate(${x} ${y})`}>
              <circle
                cx="13"
                cy="13"
                r="13"
                fill={filled ? "#1B4D3E" : "transparent"}
                stroke={filled ? "#1B4D3E" : "#D8D5CD"}
                strokeWidth="1.5"
              />
              {filled && (
                <text
                  x="13"
                  y="18"
                  textAnchor="middle"
                  fontSize="14"
                  fill="#E8A020"
                >
                  ★
                </text>
              )}
            </g>
          );
        })}
      </g>

      {/* Star row + review prompt */}
      <text
        x="340"
        y="245"
        textAnchor="middle"
        fontFamily="sans-serif"
        fontSize="10"
        fill="#5A5A5A"
      >
        Rate your visit
      </text>
      <MotionStars playing={playing} />

      {/* Confirmation pill */}
      <MotionConfirmation playing={playing} />
    </motion.g>
  );
}

/** 5 stars fade in left→right at the start of stage 4 (0.55s into cycle). */
function MotionStars({ playing }: { playing: boolean }) {
  return (
    <g transform="translate(264 256)">
      {Array.from({ length: 5 }).map((_, i) => {
        const x = i * 30;
        const delay = playing ? 0.53 + i * 0.04 : 0;
        return (
          <motion.text
            key={i}
            x={x + 10}
            y="20"
            fontSize="26"
            fill="#E8A020"
            initial={{ opacity: 0, scale: 0.6 }}
            animate={
              playing
                ? {
                    opacity: [0, 0, 1, 1, 1, 0],
                    scale: [0.6, 0.6, 1, 1, 1, 0.9],
                  }
                : { opacity: 1, scale: 1 }
            }
            transition={
              playing
                ? {
                    ...cycleTransition(),
                    times: [0, delay - 0.02, delay, 0.76, 0.9, 1],
                  }
                : { duration: 0 }
            }
          >
            ★
          </motion.text>
        );
      })}
    </g>
  );
}

/** "Review submitted ✓" pill slides up at 0.7s. */
function MotionConfirmation({ playing }: { playing: boolean }) {
  return (
    <motion.g
      initial={{ y: 16, opacity: 0 }}
      animate={
        playing
          ? { y: [16, 16, 0, 0, 0], opacity: [0, 0, 1, 1, 0] }
          : { y: 0, opacity: 1 }
      }
      transition={
        playing
          ? {
              ...cycleTransition(),
              times: [0, 0.65, 0.74, 0.9, 1],
            }
          : { duration: 0 }
      }
    >
      <rect
        x="270"
        y="290"
        width="140"
        height="30"
        rx="15"
        fill="#1B4D3E"
      />
      <text
        x="340"
        y="310"
        textAnchor="middle"
        fontFamily="sans-serif"
        fontWeight="600"
        fontSize="12"
        fill="#F7F5F0"
      >
        Review submitted ✓
      </text>
    </motion.g>
  );
}

/** Tap ripple — circle expanding from contact point at 0.36s. */
export function MotionRipple({ playing }: { playing: boolean }) {
  return (
    <motion.circle
      cx="210"
      cy="120"
      r="6"
      fill="none"
      stroke="#E8A020"
      strokeWidth="3"
      initial={{ scale: 0, opacity: 0 }}
      animate={
        playing
          ? { scale: [0, 0, 0, 4, 4], opacity: [0, 0, 0.9, 0, 0] }
          : { scale: 0, opacity: 0 }
      }
      transition={
        playing
          ? {
              ...cycleTransition(),
              ease: "easeOut",
              times: [0, 0.32, 0.36, 0.55, 1],
            }
          : { duration: 0 }
      }
      style={{ originX: "210px", originY: "120px" }}
    />
  );
}

/** Shared gradient definition. */
export function DemoDefs() {
  return (
    <defs>
      <linearGradient id="standFaceGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#245C4B" stopOpacity="0.5" />
        <stop offset="1" stopColor="#0E2D24" stopOpacity="0" />
      </linearGradient>
    </defs>
  );
}

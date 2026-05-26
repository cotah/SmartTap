"use client";

import { useEffect, useRef, useState } from "react";

import { useReducedMotion } from "./use-reduced-motion";

interface UseCounterOptions {
  /** Tween duration in milliseconds. Default 1800ms per UI/UX spec. */
  duration?: number;
  /** Set to false to hold at 0 until `start()` is called. Default true. */
  autoStart?: boolean;
}

/**
 * RequestAnimationFrame-driven counter from 0 to `target`.
 *
 * Easing is `easeOutCubic` per the visual system spec — fast initial
 * climb, soft landing. Honors `prefers-reduced-motion` by snapping
 * straight to the target value (no animation at all).
 *
 * Returns `[currentValue, restart]`. `restart` re-runs the tween from 0,
 * used by IntersectionObserver-driven counters that want to re-animate
 * each time they re-enter the viewport (rare; default is run-once).
 */
export function useCounter(
  target: number,
  { duration = 1800, autoStart = true }: UseCounterOptions = {},
): [number, () => void] {
  const reduced = useReducedMotion();
  const [value, setValue] = useState(autoStart ? 0 : 0);
  const rafRef = useRef<number | null>(null);

  function run() {
    // Reduced motion → snap to final value, skip the tween entirely.
    if (reduced) {
      setValue(target);
      return;
    }
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);

    const start = performance.now();
    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      setValue(Math.round(target * easeOutCubic(progress)));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        rafRef.current = null;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
  }

  useEffect(() => {
    if (autoStart) run();
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
    // We intentionally exclude `run` from deps — re-creating the function
    // on every render would re-trigger the effect endlessly. Target and
    // duration cover the meaningful inputs.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration, reduced, autoStart]);

  return [value, run];
}

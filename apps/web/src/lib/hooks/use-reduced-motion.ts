"use client";

import { useEffect, useState } from "react";

/**
 * SSR-safe wrapper for `prefers-reduced-motion: reduce`.
 *
 * Returns `false` during server render and on first hydration tick (since
 * `window.matchMedia` is not available on the server). All animations
 * should treat the initial render as "motion allowed" and only short-
 * circuit once this hook flips to `true` post-mount. The brief flash of
 * animation a reduced-motion user might see in that one tick is
 * acceptable for the marketing surface; the dashboard / app shell never
 * autoplays motion in the first place.
 */
export function useReducedMotion(): boolean {
  const [prefers, setPrefers] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefers(query.matches);
    // Listen for OS-level changes (rare, but cheap to support).
    const handler = (event: MediaQueryListEvent) => setPrefers(event.matches);
    query.addEventListener("change", handler);
    return () => query.removeEventListener("change", handler);
  }, []);

  return prefers;
}

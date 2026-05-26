"use client";

import { useEffect, useState } from "react";

/**
 * Returns `true` after the first client render — used to gate browser-only
 * UI like the top-banner dismiss state. Avoids hydration mismatch when the
 * server can't know whether `localStorage` says the banner was dismissed.
 */
export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  return mounted;
}

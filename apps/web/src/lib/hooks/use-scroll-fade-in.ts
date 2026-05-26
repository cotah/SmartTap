"use client";

import { useEffect, useRef, useState } from "react";

import { useReducedMotion } from "./use-reduced-motion";

interface UseScrollFadeInOptions {
  threshold?: number;
  rootMargin?: string;
  /** If true, animation only fires once even when element re-enters. */
  once?: boolean;
}

/**
 * IntersectionObserver wrapper for scroll-triggered fade-ins.
 *
 * Returns `[ref, isVisible]`. Attach the ref to the element you want to
 * watch; consume `isVisible` in framer-motion `animate` prop (or any
 * conditional style).
 *
 * Reduced-motion users see `isVisible: true` immediately on mount — no
 * waiting, no animation. That's intentional: the content is the goal,
 * not the animation.
 */
export function useScrollFadeIn<T extends HTMLElement = HTMLDivElement>({
  threshold = 0.15,
  rootMargin = "-50px 0px",
  once = true,
}: UseScrollFadeInOptions = {}): [React.RefObject<T>, boolean] {
  const ref = useRef<T>(null);
  const reduced = useReducedMotion();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (reduced) {
      setVisible(true);
      return;
    }
    const node = ref.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (!entry) return;
        if (entry.isIntersecting) {
          setVisible(true);
          if (once) observer.unobserve(node);
        } else if (!once) {
          setVisible(false);
        }
      },
      { threshold, rootMargin },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold, rootMargin, once, reduced]);

  return [ref as React.RefObject<T>, visible];
}

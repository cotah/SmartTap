"use client";

import { motion, useSpring, useTransform, useMotionValue } from "framer-motion";
import * as React from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";

/**
 * Text Repel — physics-based headline effect adapted from componentry.fun
 * for our Tailwind v3 + framer-motion stack (the original ships for v4).
 *
 * Each character drifts away from the cursor with spring dynamics. We use
 * the "Subtle Drift" variant: small max displacement, gentle spring — a
 * premium breathing motion, not the bouncy-jelly gimmick.
 *
 * Coordinates are container-relative (not viewport) so the effect is
 * scroll-safe. Characters measure their own centre on mount + resize.
 *
 * Reduced motion: renders plain, static text with no pointer handler.
 *
 * Usage: pass plain text via `children` (string) so we can split into
 * characters. Markup children are NOT supported — keep the headline text-
 * only and compose around it.
 */
const REPEL_RADIUS = 90; // px — how close the cursor must get to push a char
const MAX_DRIFT = 8; // px — subtle-drift displacement cap
const FAR = -99999; // sentinel "cursor is nowhere near" position

export function TextRepel({
  children,
  className,
  as: Tag = "span",
}: {
  children: string;
  className?: string;
  as?: "span" | "h1" | "h2" | "p";
}) {
  const reduced = useReducedMotion();

  if (reduced) {
    return <Tag className={className}>{children}</Tag>;
  }

  return <TextRepelInner className={className} as={Tag}>{children}</TextRepelInner>;
}

function TextRepelInner({
  children,
  className,
  as: Tag,
}: {
  children: string;
  className?: string;
  as: "span" | "h1" | "h2" | "p";
}) {
  const containerRef = React.useRef<HTMLElement>(null);
  // Pointer position relative to the container. Starts "far away" so chars
  // rest until the cursor actually enters.
  const pointerX = useMotionValue(FAR);
  const pointerY = useMotionValue(FAR);

  const handleMove = React.useCallback(
    (e: React.PointerEvent) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      pointerX.set(e.clientX - rect.left);
      pointerY.set(e.clientY - rect.top);
    },
    [pointerX, pointerY],
  );

  const handleLeave = React.useCallback(() => {
    pointerX.set(FAR);
    pointerY.set(FAR);
  }, [pointerX, pointerY]);

  // Preserve spaces as non-repelling gaps; split the rest into chars.
  const chars = React.useMemo(() => children.split(""), [children]);

  return (
    <Tag
      ref={containerRef as React.Ref<never>}
      className={className}
      onPointerMove={handleMove}
      onPointerLeave={handleLeave}
    >
      {chars.map((char, i) =>
        char === " " ? (
          <span key={i}>{" "}</span>
        ) : (
          <RepelChar
            key={i}
            char={char}
            containerRef={containerRef}
            pointerX={pointerX}
            pointerY={pointerY}
          />
        ),
      )}
    </Tag>
  );
}

function RepelChar({
  char,
  containerRef,
  pointerX,
  pointerY,
}: {
  char: string;
  containerRef: React.RefObject<HTMLElement>;
  pointerX: ReturnType<typeof useMotionValue<number>>;
  pointerY: ReturnType<typeof useMotionValue<number>>;
}) {
  const ref = React.useRef<HTMLSpanElement>(null);
  const center = React.useRef({ x: 0, y: 0 });

  // Measure the char centre relative to the container, on mount + resize.
  React.useLayoutEffect(() => {
    const measure = () => {
      const el = ref.current;
      const container = containerRef.current;
      if (!el || !container) return;
      const r = el.getBoundingClientRect();
      const c = container.getBoundingClientRect();
      center.current = {
        x: r.left - c.left + r.width / 2,
        y: r.top - c.top + r.height / 2,
      };
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, [containerRef]);

  // Displacement away from the cursor, capped at MAX_DRIFT, falling off with
  // distance. Reads both pointer motion values via the function form.
  const driftX = useTransform(() => {
    const dx = center.current.x - pointerX.get();
    const dy = center.current.y - pointerY.get();
    const dist = Math.hypot(dx, dy);
    if (dist > REPEL_RADIUS || dist === 0) return 0;
    const force = ((REPEL_RADIUS - dist) / REPEL_RADIUS) * MAX_DRIFT;
    return (dx / dist) * force;
  });
  const driftY = useTransform(() => {
    const dx = center.current.x - pointerX.get();
    const dy = center.current.y - pointerY.get();
    const dist = Math.hypot(dx, dy);
    if (dist > REPEL_RADIUS || dist === 0) return 0;
    const force = ((REPEL_RADIUS - dist) / REPEL_RADIUS) * MAX_DRIFT;
    return (dy / dist) * force;
  });

  const x = useSpring(driftX, { stiffness: 250, damping: 18, mass: 0.6 });
  const y = useSpring(driftY, { stiffness: 250, damping: 18, mass: 0.6 });

  return (
    <motion.span ref={ref} style={{ x, y }} className="inline-block">
      {char}
    </motion.span>
  );
}

"use client";

import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import * as React from "react";

import { useReducedMotion } from "@/lib/hooks/use-reduced-motion";
import { cn } from "@/lib/utils";

/**
 * Showcase Card — premium 3D tilt + parallax frame adapted from
 * componentry.fun for our Tailwind v3 + framer-motion stack.
 *
 * The card tilts toward the cursor (perspective rotateX/rotateY with spring
 * smoothing) and a cyan glow blooms behind it. Children marked with the
 * `data-parallax` attribute shift slightly opposite the tilt for depth —
 * used to float the product render above the card surface.
 *
 * Reduced motion: static card, no tilt, glow stays (it's not motion).
 */
const MAX_TILT = 9; // degrees

export function ShowcaseCard({
  children,
  className,
  glowClassName,
}: {
  children: React.ReactNode;
  className?: string;
  /** Override the glow colour/size. Default = cyan bloom. */
  glowClassName?: string;
}) {
  const reduced = useReducedMotion();
  const ref = React.useRef<HTMLDivElement>(null);

  const rotX = useMotionValue(0);
  const rotY = useMotionValue(0);
  const springRotX = useSpring(rotX, { stiffness: 200, damping: 20 });
  const springRotY = useSpring(rotY, { stiffness: 200, damping: 20 });

  // Parallax offsets for inner `data-parallax` layers — derived from tilt.
  const parallaxX = useTransform(springRotY, [-MAX_TILT, MAX_TILT], [12, -12]);
  const parallaxY = useTransform(springRotX, [-MAX_TILT, MAX_TILT], [-12, 12]);

  function handleMove(e: React.PointerEvent) {
    if (reduced) return;
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5; // -0.5..0.5
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    rotY.set(px * MAX_TILT * 2);
    rotX.set(-py * MAX_TILT * 2);
  }

  function handleLeave() {
    rotX.set(0);
    rotY.set(0);
  }

  return (
    <div className={cn("relative", className)}>
      {/* Cyan glow bloom behind the card */}
      <div
        aria-hidden="true"
        className={cn(
          "absolute inset-6 -z-10 rounded-[40%] bg-electric-cyan/20 blur-3xl",
          glowClassName,
        )}
      />
      <motion.div
        ref={ref}
        onPointerMove={handleMove}
        onPointerLeave={handleLeave}
        style={
          reduced
            ? undefined
            : {
                rotateX: springRotX,
                rotateY: springRotY,
                transformPerspective: 1000,
              }
        }
        className={cn(
          "relative rounded-3xl border border-electric-border bg-electric-surface/60",
          "shadow-[0_24px_80px_-20px_rgba(0,0,0,0.8)] backdrop-blur-sm",
          "[transform-style:preserve-3d]",
        )}
      >
        {/* Inner content; parallax layers read the offsets via CSS var-free
         * motion through the ParallaxLayer helper below. */}
        <ParallaxContext.Provider value={{ parallaxX, parallaxY, reduced }}>
          {children}
        </ParallaxContext.Provider>
      </motion.div>
    </div>
  );
}

type ParallaxValue = {
  parallaxX: ReturnType<typeof useTransform<number, number>>;
  parallaxY: ReturnType<typeof useTransform<number, number>>;
  reduced: boolean;
};

const ParallaxContext = React.createContext<ParallaxValue | null>(null);

/**
 * Floats its children above the card surface, shifting opposite the tilt for
 * a parallax depth cue. Must be rendered inside a ShowcaseCard.
 */
export function ParallaxLayer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ctx = React.useContext(ParallaxContext);
  if (!ctx || ctx.reduced) {
    return <div className={className}>{children}</div>;
  }
  return (
    <motion.div
      style={{ x: ctx.parallaxX, y: ctx.parallaxY }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

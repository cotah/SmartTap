import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Semantic section wrapper for the landing.
 *
 * Standard `py-32 md:py-24 sm:py-18` rhythm per LANDING-SPEC.md §4. The
 * generous default vertical padding gives every section visual breathing
 * room — Stripe/Linear scale, not a typical SaaS marketing site.
 *
 * `container` enforces the 1200/1280px max-width and centers content. Use
 * `containerSize="hero"` only on Hero + CTA Final (1280px); everything
 * else uses 1200px.
 *
 * Pass `id` so anchor links (#pricing, #faq) can target the section.
 */
type SectionProps = {
  id?: string;
  className?: string;
  containerClassName?: string;
  containerSize?: "default" | "hero" | "narrow";
  /** Override the semantic element. Default `<section>`; pass `"div"` if
   * nesting inside another <section>. */
  as?: "section" | "div";
  children: React.ReactNode;
};

const containerWidths = {
  default: "max-w-[1200px]",
  hero: "max-w-[1280px]",
  // For copy-heavy blocks (FAQ, body), enforce the readable line length.
  narrow: "max-w-[680px]",
} as const;

export function Section({
  id,
  className,
  containerClassName,
  containerSize = "default",
  as: Tag = "section",
  children,
}: SectionProps) {
  return (
    <Tag
      id={id}
      className={cn(
        // py-32 desktop / py-24 tablet / py-18 mobile — explicit min screens
        // so the mobile rhythm isn't accidentally cramped on small phones.
        "py-18 sm:py-24 lg:py-32",
        // Horizontal padding pairs with the container max-width below.
        "px-6 md:px-12 lg:px-16",
        className,
      )}
    >
      <div
        className={cn(
          "mx-auto w-full",
          containerWidths[containerSize],
          containerClassName,
        )}
      >
        {children}
      </div>
    </Tag>
  );
}

/**
 * Mono-eyebrow label used above every section header. JetBrains Mono,
 * uppercase, 0.12em tracking, with a small green dot prefix that adds the
 * Linear-style structural rhythm without resorting to numbered sections.
 */
export function SectionEyebrow({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <p
      className={cn(
        "font-mono text-xs font-medium uppercase tracking-[0.12em] text-green-900",
        "flex items-center gap-2",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="inline-block h-1.5 w-1.5 rounded-full bg-amber-500"
      />
      {children}
    </p>
  );
}

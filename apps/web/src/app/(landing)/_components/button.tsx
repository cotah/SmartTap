import { cva, type VariantProps } from "class-variance-authority";
import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Landing-page Button primitive (Dark Electric, 2026-05-31).
 *
 * Three variants:
 * - `primary`   solid cyan background, near-black text, cyan glow on hover
 * - `secondary` ghost — transparent with 1px border, cyan on hover
 * - `tertiary`  link-style, cyan underline on hover, no border
 *
 * Sizes track the visual rhythm — `lg` (the default for hero CTAs) is the
 * 56-pixel touch-friendly tap target; `md` for inline CTAs; `sm` for
 * footer / nav.
 *
 * Renders as `<a>` when `href` is passed (`next/link` when internal),
 * else `<button>`. Same component for both so the visual language stays
 * exactly the same across navigations and form submissions.
 */
const buttonStyles = cva(
  cn(
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl",
    "font-sans font-semibold tracking-tight",
    "transition-[background-color,border-color,color,transform,box-shadow] duration-200",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-electric-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-electric-bg",
    "disabled:cursor-not-allowed disabled:opacity-60",
  ),
  {
    variants: {
      variant: {
        primary: cn(
          "bg-electric-cyan text-electric-bg shadow-[0_0_0_0_rgba(0,212,255,0)]",
          "hover:bg-electric-cyan-deep hover:shadow-[0_0_24px_rgba(0,212,255,0.35)]",
          "active:translate-y-px",
        ),
        secondary: cn(
          "border border-electric-border bg-transparent text-electric-text",
          "hover:border-electric-cyan hover:text-electric-cyan",
          "active:translate-y-px",
        ),
        tertiary: cn(
          "text-electric-text underline-offset-4",
          "hover:text-electric-cyan hover:underline hover:decoration-electric-cyan",
        ),
      },
      size: {
        sm: "h-9 px-3 text-sm",
        md: "h-11 px-4 text-[15px]",
        lg: "h-14 px-7 text-base",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "lg",
    },
  },
);

type ButtonOwnProps = VariantProps<typeof buttonStyles> & {
  className?: string;
  children: React.ReactNode;
};

type ButtonAsButton = ButtonOwnProps &
  Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, keyof ButtonOwnProps> & {
    href?: undefined;
  };

type ButtonAsLink = ButtonOwnProps &
  Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, keyof ButtonOwnProps> & {
    href: string;
    /** External target — when omitted we render with next/link (client
     * routing). Pass `external` for mailto:, tel:, and full URLs we want
     * to leave the SPA. */
    external?: boolean;
  };

export type LandingButtonProps = ButtonAsButton | ButtonAsLink;

export const LandingButton = React.forwardRef<HTMLElement, LandingButtonProps>(
  function LandingButton({ variant, size, className, children, ...rest }, ref) {
    const styles = cn(buttonStyles({ variant, size }), className);

    if ("href" in rest && rest.href !== undefined) {
      const { href, external, ...anchorRest } = rest;
      if (external || href.startsWith("mailto:") || href.startsWith("tel:") || href.startsWith("http")) {
        return (
          <a
            ref={ref as React.Ref<HTMLAnchorElement>}
            href={href}
            className={styles}
            {...anchorRest}
          >
            {children}
          </a>
        );
      }
      return (
        <Link
          ref={ref as React.Ref<HTMLAnchorElement>}
          href={href}
          className={styles}
          {...anchorRest}
        >
          {children}
        </Link>
      );
    }

    return (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        type={rest.type ?? "button"}
        className={styles}
        {...rest}
      >
        {children}
      </button>
    );
  },
);

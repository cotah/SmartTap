import { cva, type VariantProps } from "class-variance-authority";
import Link from "next/link";
import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Landing-page Button primitive.
 *
 * Three variants per LANDING-SPEC.md §4:
 * - `primary`   solid green-900 background, cream text, amber-500 focus
 * - `secondary` cream background, 1px green-900 border + text
 * - `tertiary`  link-style with amber underline on hover, no border
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
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2 focus-visible:ring-offset-cream",
    "disabled:cursor-not-allowed disabled:opacity-60",
  ),
  {
    variants: {
      variant: {
        primary: cn(
          "bg-green-900 text-cream shadow-sm",
          "hover:bg-green-800 hover:shadow-md",
          "active:translate-y-px",
        ),
        secondary: cn(
          "border border-green-900 bg-cream text-green-900",
          "hover:border-amber-500 hover:text-amber-600",
          "active:translate-y-px",
        ),
        tertiary: cn(
          "text-green-900 underline-offset-4",
          "hover:text-amber-600 hover:underline hover:decoration-amber-500",
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

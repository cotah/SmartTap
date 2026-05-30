import type { Config } from "tailwindcss";
// eslint-disable-next-line @typescript-eslint/no-require-imports
const animate = require("tailwindcss-animate");

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "1280px",
      },
    },
    extend: {
      colors: {
        brand: {
          green: "#1B4D3E",
          amber: "#E8A020",
          "off-white": "#F7F5F0",
          black: "#1A1A1A",
        },
        // Derived landing palette per LANDING-SPEC.md §4. green-900 +
        // amber-500 are the brand base; -50/-600/-800 are tinted/darker
        // variants for hover, highlighted card backgrounds, focus rings.
        // Amber is restricted: never on body text (2.6:1 vs cream fails AA).
        cream: "#F7F5F0",
        green: {
          50: "#EAF0EE",
          800: "#245C4B",
          900: "#1B4D3E",
        },
        amber: {
          50: "#FBF3E4",
          500: "#E8A020",
          600: "#C8861A",
        },
        neutral: {
          300: "#D8D5CD",
          600: "#5A5A5A",
          900: "#1A1A1A",
        },
        // SmartTap Dark Electric (rebrand 2026-05-31) — landing first, rest
        // of the product cascades later. See
        // docs/superpowers/specs/2026-05-31-landing-dark-electric-redesign-design.md
        // `surface`/`surface-2` are elevations of `bg` so cards don't vanish
        // on the near-black page. Cyan fails contrast on the light surface —
        // on `electric-light` it's fills/large-decorative only, never small text.
        electric: {
          bg: "#0A0A0F",
          surface: "#121219",
          "surface-2": "#1A1A24",
          border: "#1A2A3A",
          cyan: "#00D4FF",
          "cyan-deep": "#00BFEA",
          text: "#FFFFFF",
          "text-muted": "#8899AA",
          light: "#F0FAFE",
        },
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      fontFamily: {
        // Dark Electric typography (2026-05-31): Geist Sans headings, Inter
        // body, Geist Mono for eyebrows/code. Var names come from the geist
        // package (--font-geist-*) and next/font Inter (--font-inter).
        display: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      transitionTimingFunction: {
        // Default ease-out for landing — matches Linear / Stripe polish.
        // Named `smooth-out`; used by every framer-motion fade-in.
        "smooth-out": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      // Height keyframes for the Radix Accordion content panel — required
      // because `height: auto` can't be transitioned. Radix exposes the
      // pre-measured content height via the CSS var below.
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.24s cubic-bezier(0.16, 1, 0.3, 1)",
        "accordion-up": "accordion-up 0.24s cubic-bezier(0.16, 1, 0.3, 1)",
      },
    },
  },
  plugins: [animate],
};

export default config;

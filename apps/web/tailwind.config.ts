import type { Config } from "tailwindcss";

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
        display: ["var(--font-display)", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "monospace"],
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
    },
  },
  plugins: [],
};

export default config;

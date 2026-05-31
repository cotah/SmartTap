import Link from "next/link";
import * as React from "react";

import { BrandLogo } from "./brand-logo";

/**
 * Landing footer — green-dominant, three columns, GDPR-friendly microcopy.
 *
 * Section IDs are anchor targets from elsewhere on the page; external
 * routes (/privacy, /terms, /gdpr) are real pages (stubs until Phase 5
 * legal copy lands).
 *
 * The footer is intentionally NOT a Section primitive — near-black, with a
 * thin cyan-tinted top border separating it from the page. Treated as its
 * own `<footer>` element, full-bleed.
 */
const PRODUCT_LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
];

const COMPANY_LINKS = [
  { label: "Founder note", href: "/about" },
  { label: "Contact", href: "mailto:henrique@smarttap.ie" },
  { label: "Roadmap", href: "/roadmap" },
];

const LEGAL_LINKS = [
  { label: "Privacy", href: "/privacy" },
  { label: "Terms", href: "/terms" },
  { label: "GDPR", href: "/gdpr" },
];

export function Footer() {
  return (
    <footer className="border-t border-electric-border bg-electric-bg text-electric-text">
      <div className="mx-auto max-w-[1200px] px-6 py-16 md:px-12 md:py-20 lg:px-16">
        <div className="grid gap-12 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          {/* Brand + tagline */}
          <div>
            <BrandLogo size={40} variant="electric" />
            <p className="mt-6 font-display text-3xl leading-tight tracking-tight">
              TAP. CONNECT. GROW.
            </p>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-electric-text-muted">
              Built and hosted in Ireland. GDPR compliant. Your data, always.
            </p>
          </div>

          {/* Product */}
          <FooterColumn title="Product" links={PRODUCT_LINKS} />
          {/* Company */}
          <FooterColumn title="Company" links={COMPANY_LINKS} />
          {/* Legal */}
          <FooterColumn title="Legal" links={LEGAL_LINKS} />
        </div>

        <hr className="my-10 border-electric-border" />

        <div className="flex flex-col items-start justify-between gap-3 text-xs text-electric-text-muted md:flex-row md:items-center">
          <p>© {new Date().getFullYear()} SmartTap · Built in Dublin · GDPR-compliant</p>
          <p className="font-mono uppercase tracking-[0.12em]">
            smarttap.ie
          </p>
        </div>
      </div>
    </footer>
  );
}

function FooterColumn({
  title,
  links,
}: {
  title: string;
  links: { label: string; href: string }[];
}) {
  return (
    <div>
      <h2 className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-electric-cyan">
        {title}
      </h2>
      <ul className="mt-5 space-y-3 text-sm">
        {links.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="text-electric-text-muted underline-offset-4 transition-colors hover:text-electric-text hover:underline"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

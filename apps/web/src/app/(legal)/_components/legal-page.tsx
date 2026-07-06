import Link from "next/link";
import * as React from "react";

/**
 * Shared shell for /privacy, /terms, /gdpr — Dark Electric surface (the
 * legal pages are linked from the landing footer, so they follow the
 * landing's rebrand rather than the not-yet-migrated dashboard palette).
 *
 * Plain-English legal copy, written in-house. A solicitor review pass is
 * planned before heavy paid acquisition; the pages are accurate to how the
 * product actually works today.
 */
export function LegalPage({
  eyebrow = "Legal",
  title,
  intro,
  updated,
  children,
}: {
  eyebrow?: string;
  title: string;
  intro: string;
  updated: string;
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-dvh bg-electric-bg text-electric-text">
      <div className="mx-auto flex max-w-[720px] flex-col gap-10 px-6 py-20 md:px-12 md:py-24">
        <header className="flex flex-col gap-3">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-electric-cyan">
            {eyebrow}
          </p>
          <h1 className="font-display text-4xl leading-tight tracking-[-0.02em] md:text-5xl">
            {title}
          </h1>
          <p className="text-base leading-relaxed text-electric-text-muted md:text-lg">
            {intro}
          </p>
          <p className="text-sm text-electric-text-muted">
            Last updated: {updated}
          </p>
        </header>

        <div className="flex flex-col gap-10">{children}</div>

        <footer className="flex flex-col gap-4 border-t border-electric-border pt-8">
          <p className="text-sm text-electric-text-muted">
            Questions about anything on this page?{" "}
            <a
              href="mailto:support@smarttap.ie"
              className="font-medium text-electric-cyan underline-offset-4 hover:underline"
            >
              support@smarttap.ie
            </a>
          </p>
          <p>
            <Link
              href="/"
              className="text-sm text-electric-text-muted underline-offset-4 hover:text-electric-text hover:underline"
            >
              ← Back to smarttap.ie
            </Link>
          </p>
        </footer>
      </div>
    </main>
  );
}

export function LegalSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="font-display text-2xl leading-tight tracking-tight">
        {title}
      </h2>
      {children}
    </section>
  );
}

export function LegalText({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed text-electric-text-muted">
      {children}
    </p>
  );
}

export function LegalList({ items }: { items: React.ReactNode[] }) {
  return (
    <ul className="flex flex-col gap-2.5 text-[15px] leading-relaxed text-electric-text-muted">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className="mt-[9px] inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-electric-cyan"
          />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Two-column definition row used for the subprocessor table. */
export function LegalTable({
  rows,
}: {
  rows: { name: string; detail: string }[];
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-electric-border bg-electric-surface">
      {rows.map((row, i) => (
        <div
          key={row.name}
          className={`grid gap-1 p-4 sm:grid-cols-[180px_1fr] sm:gap-4 ${
            i > 0 ? "border-t border-electric-border" : ""
          }`}
        >
          <p className="text-sm font-medium text-electric-text">{row.name}</p>
          <p className="text-sm leading-relaxed text-electric-text-muted">
            {row.detail}
          </p>
        </div>
      ))}
    </div>
  );
}

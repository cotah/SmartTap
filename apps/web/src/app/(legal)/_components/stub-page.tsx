import Link from "next/link";
import * as React from "react";

/**
 * Shared stub used by /privacy, /terms, /gdpr until the full legal copy
 * is drafted by a solicitor. Lists what the page will eventually cover
 * (so the page reads as a sincere placeholder, not a 404) and provides
 * a direct contact route for anyone who needs the info now.
 *
 * Real copy lands in the Phase 5 follow-up; until then this avoids dead
 * links in the footer.
 */
export function LegalStub({
  title,
  description,
  outline,
}: {
  title: string;
  description: string;
  outline: string[];
}) {
  return (
    <main className="mx-auto flex min-h-dvh max-w-[680px] flex-col gap-8 px-6 py-20 md:px-12 md:py-24">
      <header className="flex flex-col gap-3">
        <p className="font-mono text-xs font-medium uppercase tracking-[0.12em] text-amber-600">
          Coming soon
        </p>
        <h1 className="font-display text-4xl leading-tight tracking-[-0.02em] text-neutral-900 md:text-5xl">
          {title}
        </h1>
        <p className="text-base leading-relaxed text-neutral-600 md:text-lg">
          {description}
        </p>
      </header>

      <section className="rounded-2xl border border-neutral-300 bg-cream/70 p-6 md:p-8">
        <h2 className="font-display text-xl leading-tight tracking-tight">
          The full page will cover
        </h2>
        <ul className="mt-4 flex flex-col gap-2 text-base leading-relaxed text-neutral-600">
          {outline.map((line) => (
            <li key={line} className="flex items-start gap-2">
              <span
                aria-hidden="true"
                className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"
              />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </section>

      <p className="text-sm text-neutral-600">
        Need the detail now?{" "}
        <a
          href="mailto:henrique@smarttap.ie"
          className="font-medium text-green-900 underline-offset-4 hover:text-amber-600 hover:underline"
        >
          henrique@smarttap.ie
        </a>
      </p>

      <p>
        <Link
          href="/"
          className="text-sm text-neutral-600 underline-offset-4 hover:text-green-900 hover:underline"
        >
          ← Back to smarttap.ie
        </Link>
      </p>
    </main>
  );
}

"use client";

// Error boundary for the whole /dashboard subtree (S5 audit F1). Previously a
// failed server-component fetch (e.g. the API momentarily down) bubbled past
// the dashboard with no boundary. This catches it and offers a retry.
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex min-h-[50vh] flex-col items-center justify-center gap-4 text-center">
      <div>
        <h1 className="font-display text-2xl font-semibold text-electric-text">Something went wrong</h1>
        <p className="mt-2 text-sm text-electric-text-muted">
          We couldn&rsquo;t load this page. This is usually temporary.
        </p>
        {error.digest ? (
          <p className="mt-1 text-xs text-electric-text-muted/70">Reference: {error.digest}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={reset}
        className="rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg"
      >
        Try again
      </button>
    </main>
  );
}

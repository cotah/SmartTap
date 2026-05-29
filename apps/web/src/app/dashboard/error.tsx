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
        <h1 className="font-display text-2xl text-brand-black">Something went wrong</h1>
        <p className="mt-2 text-sm text-brand-black/60">
          We couldn&rsquo;t load this page. This is usually temporary.
        </p>
        {error.digest ? (
          <p className="mt-1 text-xs text-brand-black/40">Reference: {error.digest}</p>
        ) : null}
      </div>
      <button
        type="button"
        onClick={reset}
        className="rounded-full bg-brand-green px-5 py-2.5 text-sm font-semibold text-brand-off-white"
      >
        Try again
      </button>
    </main>
  );
}

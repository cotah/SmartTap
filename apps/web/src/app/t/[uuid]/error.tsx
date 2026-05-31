"use client";

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function CustomerTapError({ reset }: Props) {
  return (
    <main className="container flex min-h-dvh flex-col items-center justify-center gap-4 bg-electric-bg text-center text-electric-text">
      <h1 className="font-display text-3xl font-semibold">Something went wrong.</h1>
      <p className="text-electric-text-muted">
        Tap again, or ask the shop owner. We&apos;re looking into it.
      </p>
      <button type="button" onClick={reset} className="text-electric-cyan underline">
        Try again
      </button>
    </main>
  );
}

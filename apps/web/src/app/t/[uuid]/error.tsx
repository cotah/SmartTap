"use client";

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function CustomerTapError({ reset }: Props) {
  return (
    <main className="container flex min-h-dvh flex-col items-center justify-center gap-4 text-center">
      <h1 className="font-display text-3xl">Something went wrong.</h1>
      <p className="text-muted-foreground">
        Tap again, or ask the shop owner. We&apos;re looking into it.
      </p>
      <button type="button" onClick={reset} className="underline">
        Try again
      </button>
    </main>
  );
}

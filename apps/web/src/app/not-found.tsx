import Link from "next/link";

export default function NotFound() {
  return (
    <main className="container flex min-h-dvh flex-col items-center justify-center gap-4 text-center">
      <h1 className="font-display text-5xl">404</h1>
      <p className="text-muted-foreground">This page does not exist.</p>
      <Link href="/" className="underline">
        Go home
      </Link>
    </main>
  );
}

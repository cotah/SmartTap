import { notFound } from "next/navigation";

interface PageProps {
  params: Promise<{ uuid: string }>;
}

export default async function CustomerTapPage({ params }: PageProps) {
  const { uuid } = await params;

  if (!/^[0-9a-f-]{36}$/i.test(uuid)) {
    notFound();
  }

  return (
    <main className="min-h-dvh bg-brand-green text-brand-off-white">
      <section className="container flex min-h-dvh flex-col items-center justify-center gap-6 py-12 text-center">
        <p className="text-sm tracking-widest opacity-70">SMARTTAP</p>
        <h1 className="font-display text-4xl">Tap received.</h1>
        <p className="opacity-80">
          Customer view skeleton. Tag: <code className="font-mono">{uuid}</code>
        </p>
        <p className="text-sm opacity-60">
          Sprint 1 wires this to the API: tap logging, stamp engine, review CTA.
        </p>
      </section>
    </main>
  );
}

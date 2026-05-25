export default function HomePage() {
  return (
    <main className="min-h-dvh bg-brand-off-white text-brand-black">
      <section className="container flex min-h-dvh flex-col items-center justify-center gap-6 py-24 text-center">
        <p className="text-sm tracking-widest text-brand-green">
          BUILT IN DUBLIN · FOR LOCAL BUSINESSES
        </p>
        <h1 className="font-display text-5xl leading-tight md:text-7xl">
          One tap.
          <br />
          Reviews go up.
          <br />
          Regulars come back.
        </h1>
        <p className="max-w-xl text-lg text-muted-foreground">
          The only loyalty and reviews system for Dublin businesses where the data,
          the customer, and the stand on your counter belong to you. From €29/month.
          No app required.
        </p>
        <p className="text-sm text-muted-foreground">
          Landing page placeholder — full design coming in Sprint 1.
        </p>
      </section>
    </main>
  );
}

import type { TapResponse } from "@/lib/api";

interface Props {
  data: TapResponse;
}

export function TapView({ data }: Props) {
  const { tenant, customer, reward_state, reward_available } = data;
  const bg = tenant.primary_color;
  const accent = tenant.accent_color;
  const greeting = customer?.name ? `Welcome back, ${customer.name.split(" ")[0]}` : "Hi there 👋";

  return (
    <main className="min-h-dvh text-brand-off-white" style={{ backgroundColor: bg }}>
      <div className="container flex min-h-dvh flex-col gap-8 py-10">
        <header className="flex flex-col items-center gap-2 text-center">
          {tenant.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element -- next/image with remotePatterns lands in S1-W6
            <img src={tenant.logo_url} alt={tenant.name} className="h-16 w-auto" />
          ) : null}
          <p className="text-xs tracking-[0.3em] opacity-70">SMARTTAP</p>
          <h1 className="font-display text-3xl">{tenant.name}</h1>
        </header>

        <section className="flex flex-1 flex-col items-center justify-center gap-6 text-center">
          <p className="font-display text-2xl">{greeting}</p>

          {reward_available ? (
            <div
              className="rounded-2xl bg-white/95 px-8 py-6 text-brand-black shadow-lg"
              style={{ borderColor: accent, borderWidth: 2, borderStyle: "solid" }}
            >
              <p className="text-sm uppercase tracking-widest" style={{ color: accent }}>
                🎁 Your reward
              </p>
              <p className="mt-2 font-display text-2xl">{reward_available.description}</p>
              <p className="mt-4 font-mono text-4xl tracking-widest">
                {reward_available.validation_code.replace(/(\d{3})(\d{3})/, "$1 $2")}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">Show this code to the staff</p>
            </div>
          ) : (
            <StampProgress state={reward_state} accent={accent} />
          )}

          {data.stamp_awarded ? (
            <p className="text-sm" style={{ color: accent }}>
              ✓ Stamp added · {reward_state.current_stamps} / {reward_state.stamps_for_reward}
            </p>
          ) : null}

          <div className="flex flex-col gap-3">
            <button
              type="button"
              className="rounded-full px-6 py-3 font-semibold"
              style={{ backgroundColor: accent, color: "#1A1A1A" }}
            >
              ⭐ Leave a Google Review
            </button>
            {customer === null ? (
              <button
                type="button"
                className="rounded-full border border-white/40 px-6 py-3 text-sm"
              >
                📱 Sign up for offers
              </button>
            ) : null}
          </div>
        </section>

        <footer className="text-center text-xs opacity-60">
          Powered by SmartTap · <a href="/privacy">Privacy</a> ·{" "}
          <a href="/data-request">Delete my data</a>
        </footer>
      </div>
    </main>
  );
}

function StampProgress({
  state,
  accent,
}: {
  state: TapResponse["reward_state"];
  accent: string;
}) {
  return (
    <div className="flex flex-col items-center gap-3">
      <p className="font-display text-5xl">
        {state.current_stamps}
        <span className="text-2xl opacity-60"> / {state.stamps_for_reward}</span>
      </p>
      <p className="text-sm opacity-70">
        {state.stamps_remaining === 0
          ? "Reward unlocked!"
          : `${state.stamps_remaining} more to your reward`}
      </p>
      <div
        className="h-2 w-48 overflow-hidden rounded-full"
        style={{ backgroundColor: "rgba(255,255,255,0.2)" }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${state.progress_percent}%`, backgroundColor: accent }}
        />
      </div>
    </div>
  );
}

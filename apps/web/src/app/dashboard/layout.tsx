import { getDashboardContext } from "@/lib/dashboard-data";

import { SignOutButton } from "./sign-out-button";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const ctx = await getDashboardContext();
  const trialDays = trialDaysRemaining(ctx.tenant.trial_ends_at);

  return (
    <div className="min-h-dvh bg-brand-off-white text-brand-black">
      <header className="border-b border-brand-black/10 bg-white">
        <div className="container flex items-center justify-between py-4">
          <div>
            <p className="text-xs tracking-[0.3em] text-brand-green">SMARTTAP</p>
            <p className="font-display text-xl">{ctx.tenant.name}</p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            {ctx.tenant.plan === "trial" && trialDays !== null ? (
              <span className="rounded-full bg-brand-amber/10 px-3 py-1 text-xs font-semibold text-brand-amber">
                Trial · {trialDays}d left
              </span>
            ) : null}
            <span className="hidden text-brand-black/60 md:inline">{ctx.email}</span>
            <SignOutButton />
          </div>
        </div>
      </header>
      <div className="container py-8">{children}</div>
    </div>
  );
}

function trialDaysRemaining(trialEndsAt: string | null): number | null {
  if (!trialEndsAt) return null;
  const ends = new Date(trialEndsAt).getTime();
  if (Number.isNaN(ends)) return null;
  const diff = ends - Date.now();
  if (diff <= 0) return 0;
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

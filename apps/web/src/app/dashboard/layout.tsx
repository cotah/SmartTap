import { getDashboardContext } from "@/lib/dashboard-data";

import { SignOutButton } from "./sign-out-button";
import { TrialBanner } from "./trial-banner";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const ctx = await getDashboardContext();

  return (
    <div className="min-h-dvh bg-brand-off-white text-brand-black">
      <TrialBanner
        status={ctx.tenant.trial_status}
        trialEndsAt={ctx.tenant.trial_ends_at}
      />
      <header className="border-b border-brand-black/10 bg-white">
        <div className="container flex items-center justify-between py-4">
          <div>
            <p className="text-xs tracking-[0.3em] text-brand-green">SMARTTAP</p>
            <p className="font-display text-xl">{ctx.tenant.name}</p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="hidden text-brand-black/60 md:inline">{ctx.email}</span>
            <SignOutButton />
          </div>
        </div>
      </header>
      <div className="container py-8">{children}</div>
    </div>
  );
}

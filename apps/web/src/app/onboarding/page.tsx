import { redirect } from "next/navigation";

import { getOnboardingContext } from "@/lib/dashboard-data";

import { OnboardingForm } from "./onboarding-form";

export default async function OnboardingPage() {
  const ctx = await getOnboardingContext();
  if (ctx.tenant.onboarding_complete) {
    redirect("/dashboard");
  }

  return (
    <main className="min-h-dvh bg-brand-off-white text-brand-black">
      <div className="container max-w-2xl space-y-8 py-12">
        <header className="space-y-2">
          <p className="text-xs tracking-[0.3em] text-brand-green">SMARTTAP</p>
          <h1 className="font-display text-4xl">Let&rsquo;s set up your business</h1>
          <p className="text-brand-black/60">
            A few quick questions and you&rsquo;re ready to start collecting taps.
          </p>
        </header>

        <OnboardingForm
          initialName={
            ctx.tenant.name === "My business" ? "" : ctx.tenant.name
          }
        />
      </div>
    </main>
  );
}

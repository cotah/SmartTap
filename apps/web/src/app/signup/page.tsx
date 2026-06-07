import { BrandLogo } from "@/app/(landing)/_components/brand-logo";

import { SignupForm } from "./signup-form";

export default function SignupPage() {
  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-electric-bg px-4 py-12 text-electric-text">
      {/* Ambient cyan glows */}
      <div
        className="pointer-events-none absolute -left-[5%] -top-[10%] -z-10 h-[40%] w-[40%] rounded-full bg-electric-cyan/10 blur-3xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -bottom-[10%] -right-[5%] -z-10 h-[30%] w-[30%] rounded-full bg-electric-cyan/10 blur-3xl"
        aria-hidden="true"
      />

      {/* Signup card */}
      <div className="relative z-10 w-full max-w-[480px] animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="rounded-xl border border-electric-border bg-electric-surface p-8 shadow-[0_8px_32px_rgba(0,0,0,0.4)] transition-shadow duration-300 hover:shadow-[0_12px_48px_rgba(0,212,255,0.08)] md:p-10">
          <div className="mb-10 flex justify-center">
            <BrandLogo variant="electric" size={40} withWordmark />
          </div>

          <div className="mb-8 text-center">
            <h1 className="font-display text-3xl leading-tight text-electric-text">
              Create your account
            </h1>
            <p className="mt-2 text-sm text-electric-text-muted">
              Free 30-day trial. No credit card required.
            </p>
          </div>

          <SignupForm />
        </div>
      </div>
    </main>
  );
}

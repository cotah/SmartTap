import { BrandLogo } from "@/app/(landing)/_components/brand-logo";

import { LoginForm } from "./login-form";

interface PageProps {
  searchParams: Promise<{ error?: string }>;
}

export default async function LoginPage({ searchParams }: PageProps) {
  const params = await searchParams;

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

      {/* Login card */}
      <div className="relative z-10 w-full max-w-[480px] animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="rounded-xl border border-electric-border bg-electric-surface p-8 shadow-[0_8px_32px_rgba(0,0,0,0.4)] transition-shadow duration-300 hover:shadow-[0_12px_48px_rgba(0,212,255,0.08)] md:p-10">
          {/* Brand logo */}
          <div className="mb-10 flex justify-center">
            <BrandLogo variant="electric" size={40} withWordmark />
          </div>

          {/* Header */}
          <div className="mb-8 text-center">
            <h1 className="font-display text-3xl leading-tight text-electric-text">
              Welcome back
            </h1>
            <p className="mt-2 text-sm text-electric-text-muted">
              Sign in to manage your business dashboard.
            </p>
          </div>

          {params.error === "auth_callback_failed" ? (
            <p className="mb-6 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">
              Sign-in link expired or invalid. Try again.
            </p>
          ) : null}

          <LoginForm />
        </div>
      </div>
    </main>
  );
}

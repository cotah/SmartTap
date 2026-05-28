import { SignupForm } from "./signup-form";

export default function SignupPage() {
  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden bg-brand-off-white px-4 py-12">
      {/* Ambient background blurs */}
      <div
        className="pointer-events-none absolute -left-[5%] -top-[10%] -z-10 h-[40%] w-[40%] rounded-full bg-brand-green/15 blur-3xl"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute -bottom-[10%] -right-[5%] -z-10 h-[30%] w-[30%] rounded-full bg-brand-amber/15 blur-3xl"
        aria-hidden="true"
      />

      {/* Signup card */}
      <div className="relative z-10 w-full max-w-[480px] animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="rounded-xl border border-neutral-300/30 bg-white p-8 shadow-[0_8px_32px_rgba(27,77,62,0.08)] transition-shadow duration-300 hover:shadow-[0_12px_48px_rgba(27,77,62,0.12)] md:p-10">
          <div className="mb-10 flex justify-center">
            <p className="font-display text-3xl tracking-tight text-brand-green">
              SmartTap
            </p>
          </div>

          <div className="mb-8 text-center">
            <h1 className="font-display text-3xl leading-tight text-brand-green">
              Create your account
            </h1>
            <p className="mt-2 text-sm text-neutral-600">
              Free 30-day trial. No credit card required.
            </p>
          </div>

          <SignupForm />
        </div>
      </div>
    </main>
  );
}

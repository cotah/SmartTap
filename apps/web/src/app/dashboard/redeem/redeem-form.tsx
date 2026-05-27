"use client";

import { BadgeCheck, CheckCircle2, Lock } from "lucide-react";
import { type FormEvent, useRef, useState, useTransition } from "react";

import { type RedeemResult, redeemByCodeAction } from "./actions";

export function RedeemForm() {
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<RedeemResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const code = String(fd.get("validation_code") ?? "");
    setResult(null);
    startTransition(async () => {
      const r = await redeemByCodeAction(code);
      setResult(r);
      if (!r.ok) {
        inputRef.current?.select();
      }
    });
  }

  function reset() {
    setResult(null);
    inputRef.current?.focus();
  }

  if (result?.ok) {
    return (
      <SuccessCard
        description={result.description}
        customerName={result.customer_name}
        onReset={reset}
      />
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-8 rounded-xl border border-brand-green/5 bg-white p-6 shadow-[0_4px_24px_rgba(27,77,62,0.04)] md:p-8"
    >
      <div className="space-y-2">
        <label
          htmlFor="validation_code"
          className="block text-xs font-bold uppercase tracking-wider text-brand-black"
        >
          Customer code
        </label>
        <p className="text-sm text-neutral-600">
          Enter the 6-digit pin from the customer&apos;s loyalty card.
        </p>
        <input
          ref={inputRef}
          id="validation_code"
          name="validation_code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="\d{6}"
          maxLength={6}
          required
          autoFocus
          placeholder="000000"
          className="mt-3 w-full rounded-lg border-2 border-brand-green/20 bg-brand-off-white px-4 py-5 text-center font-mono text-4xl tracking-[0.4em] text-brand-green shadow-[inset_0_2px_4px_rgba(27,77,62,0.05)] outline-none transition-colors placeholder:text-neutral-600/30 focus:border-brand-amber focus:ring-2 focus:ring-brand-amber/30"
        />
      </div>

      {result && !result.ok ? (
        <div
          role="alert"
          className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {result.message}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-green px-6 py-4 text-sm font-bold uppercase tracking-wider text-white shadow-sm transition-colors hover:bg-green-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? (
          <>
            <Lock className="h-4 w-4" aria-hidden="true" />
            Validating…
          </>
        ) : (
          "Validate and redeem"
        )}
      </button>
    </form>
  );
}

function SuccessCard({
  description,
  customerName,
  onReset,
}: {
  description: string;
  customerName: string | null;
  onReset: () => void;
}) {
  return (
    <div
      role="status"
      className="relative overflow-hidden rounded-xl bg-brand-green p-8 text-center text-white shadow-[0_8px_24px_rgba(27,77,62,0.12)]"
    >
      {/* Decorative blurs */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-brand-amber opacity-20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-12 -left-12 h-32 w-32 rounded-full bg-white opacity-5 blur-2xl" />

      <div className="relative z-10 flex flex-col items-center gap-6">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-bold uppercase tracking-wider backdrop-blur-md">
          <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
          Verified
        </span>

        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-brand-amber text-brand-green shadow-lg">
          <CheckCircle2 className="h-10 w-10" aria-hidden="true" />
        </div>

        <div>
          <h2 className="font-display text-3xl leading-tight">
            Reward redeemed
          </h2>
          {customerName ? (
            <p className="mt-1 text-sm text-white/80">
              for <strong className="font-bold">{customerName}</strong>
            </p>
          ) : null}
        </div>

        {/* Reward description card */}
        <div className="w-full rounded-xl bg-white p-5 text-left text-brand-black shadow-[0_4px_12px_rgba(0,0,0,0.1)]">
          <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-600">
            Item dispensed
          </p>
          <p className="mt-1 font-display text-xl text-brand-green">
            {description}
          </p>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="rounded-lg border border-white/30 px-6 py-3 text-sm font-bold uppercase tracking-wider text-white transition-colors hover:bg-white/10"
        >
          Redeem another
        </button>
      </div>
    </div>
  );
}

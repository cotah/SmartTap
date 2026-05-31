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
      className="space-y-8 rounded-xl border border-electric-border bg-electric-surface p-6 shadow-[0_4px_24px_rgba(0,0,0,0.04)] md:p-8"
    >
      <div className="space-y-2">
        <label
          htmlFor="validation_code"
          className="block text-xs font-bold uppercase tracking-wider text-electric-text"
        >
          Customer code
        </label>
        <p className="text-sm text-electric-text-muted">
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
          className="mt-3 w-full rounded-lg border-2 border-electric-border bg-electric-surface-2 px-4 py-5 text-center font-mono text-4xl tracking-[0.4em] text-electric-cyan shadow-[inset_0_2px_4px_rgba(0,0,0,0.05)] outline-none transition-colors placeholder:text-electric-text-muted focus:border-electric-cyan focus:ring-2 focus:ring-electric-cyan/30"
        />
      </div>

      {result && !result.ok ? (
        <div
          role="alert"
          className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-300"
        >
          {result.message}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-electric-cyan px-6 py-4 text-sm font-bold uppercase tracking-wider text-electric-bg shadow-sm transition-colors hover:bg-electric-cyan-deep disabled:cursor-not-allowed disabled:opacity-60"
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
      className="relative overflow-hidden rounded-xl bg-electric-cyan p-8 text-center text-electric-bg shadow-[0_8px_24px_rgba(0,0,0,0.12)]"
    >
      {/* Decorative blurs */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-electric-cyan opacity-20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-12 -left-12 h-32 w-32 rounded-full bg-electric-surface opacity-5 blur-2xl" />

      <div className="relative z-10 flex flex-col items-center gap-6">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-electric-surface/10 px-3 py-1 text-xs font-bold uppercase tracking-wider backdrop-blur-md">
          <BadgeCheck className="h-3.5 w-3.5" aria-hidden="true" />
          Verified
        </span>

        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-electric-cyan text-electric-cyan shadow-lg">
          <CheckCircle2 className="h-10 w-10" aria-hidden="true" />
        </div>

        <div>
          <h2 className="font-display text-3xl leading-tight">
            Reward redeemed
          </h2>
          {customerName ? (
            <p className="mt-1 text-sm text-electric-bg/80">
              for <strong className="font-bold">{customerName}</strong>
            </p>
          ) : null}
        </div>

        {/* Reward description card */}
        <div className="w-full rounded-xl bg-electric-surface p-5 text-left text-electric-text shadow-[0_4px_12px_rgba(0,0,0,0.1)]">
          <p className="text-[10px] font-bold uppercase tracking-widest text-electric-text-muted">
            Item dispensed
          </p>
          <p className="mt-1 font-display text-xl text-electric-cyan">
            {description}
          </p>
        </div>

        <button
          type="button"
          onClick={onReset}
          className="rounded-lg border border-white/30 px-6 py-3 text-sm font-bold uppercase tracking-wider text-electric-bg transition-colors hover:bg-electric-surface/10"
        >
          Redeem another
        </button>
      </div>
    </div>
  );
}

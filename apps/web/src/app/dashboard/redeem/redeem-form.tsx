"use client";

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
        // Keep focus on the input so they can fix and retry.
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
      className="space-y-6 rounded-2xl border border-brand-black/10 bg-white p-6 shadow-sm"
    >
      <div className="space-y-2">
        <label htmlFor="validation_code" className="block text-sm font-semibold">
          6-digit code
        </label>
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
          className="w-full rounded-lg border border-brand-black/20 px-4 py-4 text-center font-mono text-4xl tracking-[0.5em] outline-none focus:border-brand-green"
        />
      </div>

      {result && !result.ok ? (
        <div
          role="alert"
          className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {result.message}
        </div>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-full bg-brand-green px-6 py-3 font-semibold text-brand-off-white disabled:opacity-60"
      >
        {pending ? "Validating…" : "Validate and redeem"}
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
      className="space-y-4 rounded-2xl border border-brand-green/30 bg-brand-green/5 p-8 text-center shadow-sm"
    >
      <p className="text-5xl">✓</p>
      <div>
        <p className="font-display text-2xl">Redeemed</p>
        <p className="mt-1 text-brand-black/70">
          {customerName ? <strong>{customerName}</strong> : "Customer"} gets:{" "}
          <strong>{description}</strong>
        </p>
      </div>
      <button
        type="button"
        onClick={onReset}
        className="rounded-full border border-brand-green px-6 py-2 text-sm font-semibold text-brand-green"
      >
        Redeem another
      </button>
    </div>
  );
}

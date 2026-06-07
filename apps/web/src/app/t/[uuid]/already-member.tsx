"use client";

import { KeyRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { requestCodeAction, verifyCodeAction } from "./actions";

interface Props {
  tenantId: string;
}

/**
 * Sprint 5.6 — "Already a member?" recovery on /t/[uuid].
 *
 * Sits below the loyalty opt-in form, visually quieter (it's the rarer path:
 * a returning customer who lost their cookie). Two steps: enter phone → enter
 * the 4-digit SMS code. On success the verify action sets the magic cookie and
 * we refresh, which re-taps and restores the customer's stamps.
 */
export function AlreadyMember({ tenantId }: Props) {
  const router = useRouter();
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("+353");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function sendCode() {
    setError(null);
    startTransition(async () => {
      const result = await requestCodeAction(tenantId, phone);
      if (result.ok) {
        setStep("code");
      } else {
        setError(result.error);
      }
    });
  }

  function verify() {
    setError(null);
    startTransition(async () => {
      const result = await verifyCodeAction(tenantId, phone, code);
      if (result.ok) {
        router.refresh();
      } else {
        setError(result.error);
      }
    });
  }

  return (
    <div className="mt-4 w-full rounded-xl border border-electric-border/70 bg-electric-surface/60 p-5 text-left">
      <div className="flex items-center gap-2.5">
        <KeyRound className="h-4 w-4 text-electric-text-muted" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-electric-text">
          Already a member?
        </h3>
      </div>

      {step === "phone" ? (
        <>
          <p className="mt-1 text-xs text-electric-text-muted">
            Recover your stamps with your phone number. We&apos;ll text you a
            4-digit code. We won&apos;t add you to any list.
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <label htmlFor="member-phone" className="sr-only">
              Phone number
            </label>
            <input
              id="member-phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+353 86 123 4567"
              className="flex-1 rounded-lg border border-electric-border bg-electric-surface-2 px-4 py-3 text-base text-electric-text outline-none transition-all placeholder:text-electric-text-muted/50 focus:ring-2 focus:ring-electric-cyan"
            />
            <button
              type="button"
              onClick={sendCode}
              disabled={pending}
              className="shrink-0 rounded-lg border border-electric-cyan/60 px-5 py-3 text-sm font-semibold text-electric-cyan transition-colors hover:bg-electric-cyan/10 disabled:opacity-60"
            >
              {pending ? "Sending…" : "Send code"}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="mt-1 text-xs text-electric-text-muted">
            If <strong className="text-electric-text">{phone}</strong> is on file,
            we just texted a 4-digit code.
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <label htmlFor="member-code" className="sr-only">
              4-digit code
            </label>
            <input
              id="member-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={4}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="1234"
              className="flex-1 rounded-lg border border-electric-border bg-electric-surface-2 px-4 py-3 text-center text-2xl tracking-[0.5em] text-electric-text outline-none transition-all placeholder:text-electric-text-muted/40 focus:ring-2 focus:ring-electric-cyan"
            />
            <button
              type="button"
              onClick={verify}
              disabled={pending}
              className="shrink-0 rounded-lg bg-electric-cyan px-5 py-3 text-sm font-bold uppercase tracking-wider text-electric-bg transition-colors hover:bg-electric-cyan-deep disabled:opacity-60"
            >
              {pending ? "Checking…" : "Verify"}
            </button>
          </div>
          <button
            type="button"
            onClick={() => {
              setStep("phone");
              setCode("");
              setError(null);
            }}
            className="mt-2 text-xs text-electric-text-muted underline"
          >
            Use a different number
          </button>
        </>
      )}

      {error ? <p className="mt-2 text-xs text-red-300">{error}</p> : null}
    </div>
  );
}

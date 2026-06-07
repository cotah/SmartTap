"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Check, Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { useForm } from "react-hook-form";

import { type CustomerIdentify, customerIdentifySchema } from "@smarttap/core";

import { optInAction } from "./actions";
import { AlreadyMember } from "./already-member";

const CONSENT_TEXT =
  "I agree to receive offers and updates from this business via SMS or WhatsApp. " +
  "I can ask to be removed at any time.";

interface Props {
  tenantId: string;
  tenantName: string;
}

/**
 * Secondary CTA on /t/[uuid] — opt-in for the loyalty card.
 *
 * Visual treatment is intentionally subordinate to the Review button
 * above: white card, smaller heading, soft ambient shadow, sits below
 * the fold. Returning (opted-in) customers don't see this at all —
 * TapView only renders the form when `customer === null`.
 */
export function OptInForm({ tenantId, tenantName }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CustomerIdentify>({
    resolver: zodResolver(customerIdentifySchema),
    defaultValues: {
      tenant_id: tenantId,
      phone: "+353",
      gdpr_consent: undefined,
      gdpr_consent_text: CONSENT_TEXT,
    },
  });

  const onSubmit = (data: CustomerIdentify) => {
    setServerError(null);
    startTransition(async () => {
      const result = await optInAction(data);
      if (result.ok) {
        router.refresh();
      } else {
        setServerError(result.error);
      }
    });
  };

  return (
    <div className="flex w-full flex-col">
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex w-full flex-col rounded-xl border border-electric-border bg-electric-surface p-6 text-left text-electric-text shadow-[0_4px_24px_rgba(0,0,0,0.4)]"
    >
      <div className="mb-2 flex items-center gap-3">
        <Mail className="h-5 w-5 text-electric-cyan" aria-hidden="true" />
        <h3 className="font-display text-xl font-semibold leading-tight text-electric-text">
          Keep your stamps in your pocket
        </h3>
      </div>
      <p className="mb-6 text-sm text-electric-text-muted">
        Join {tenantName}&apos;s loyalty card. One tap, no app, no spam.
      </p>

      <input type="hidden" {...register("tenant_id")} />
      <input type="hidden" {...register("gdpr_consent_text")} />

      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="opt-in-name"
            className="ml-1 text-xs font-medium text-electric-text-muted"
          >
            Name (optional)
          </label>
          <input
            id="opt-in-name"
            type="text"
            autoComplete="given-name"
            placeholder="Sean"
            {...register("name")}
            className="rounded-lg border border-electric-border bg-electric-surface-2 px-4 py-3.5 text-base text-electric-text outline-none transition-all placeholder:text-electric-text-muted/50 focus:border-transparent focus:ring-2 focus:ring-electric-cyan"
          />
          {errors.name ? (
            <span className="text-xs text-red-300">{errors.name.message}</span>
          ) : null}
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="opt-in-phone"
            className="ml-1 text-xs font-medium text-electric-text-muted"
          >
            Phone number
          </label>
          <input
            id="opt-in-phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="+353 86 123 4567"
            {...register("phone")}
            className="rounded-lg border border-electric-border bg-electric-surface-2 px-4 py-3.5 text-base text-electric-text outline-none transition-all placeholder:text-electric-text-muted/50 focus:border-transparent focus:ring-2 focus:ring-electric-cyan"
          />
          {errors.phone ? (
            <span className="text-xs text-red-300">{errors.phone.message}</span>
          ) : null}
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="opt-in-email"
            className="ml-1 text-xs font-medium text-electric-text-muted"
          >
            Email (optional)
          </label>
          <input
            id="opt-in-email"
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder="sean@example.com"
            {...register("email")}
            className="rounded-lg border border-electric-border bg-electric-surface-2 px-4 py-3.5 text-base text-electric-text outline-none transition-all placeholder:text-electric-text-muted/50 focus:border-transparent focus:ring-2 focus:ring-electric-cyan"
          />
          {errors.email ? (
            <span className="text-xs text-red-300">{errors.email.message}</span>
          ) : null}
        </div>

        <label className="-ml-2 mt-1 flex cursor-pointer items-start gap-3 rounded-lg p-2 transition-colors hover:bg-electric-surface-2">
          <span className="relative mt-0.5 flex shrink-0 items-center justify-center">
            <input
              type="checkbox"
              {...register("gdpr_consent")}
              className="peer h-5 w-5 cursor-pointer appearance-none rounded border-2 border-electric-border bg-electric-surface-2 transition-colors checked:border-electric-cyan checked:bg-electric-cyan focus:outline-none focus:ring-2 focus:ring-electric-cyan"
            />
            <Check
              aria-hidden="true"
              className="pointer-events-none absolute h-3.5 w-3.5 text-electric-bg opacity-0 peer-checked:opacity-100"
            />
          </span>
          <span className="flex-1 text-xs leading-relaxed text-electric-text-muted">
            I agree to receive offers from <strong>{tenantName}</strong> via SMS
            or WhatsApp. I can ask to be removed at any time.
          </span>
        </label>
        {errors.gdpr_consent ? (
          <span className="text-xs text-red-300">
            {errors.gdpr_consent.message}
          </span>
        ) : null}

        {serverError ? (
          <p className="text-sm text-red-300">{serverError}</p>
        ) : null}

        <button
          type="submit"
          disabled={isPending}
          className="mt-2 w-full rounded-lg bg-electric-cyan px-6 py-4 text-sm font-bold uppercase tracking-wider text-electric-bg shadow-sm transition-colors hover:bg-electric-cyan-deep active:scale-[0.98] disabled:opacity-60"
        >
          {isPending ? "Saving…" : "Join loyalty card"}
        </button>
      </div>
    </form>
      {/* Sprint 5.6 — gated off until the OTP infra is live (migration 012
          applied + Twilio configured). Flip NEXT_PUBLIC_OTP_ENABLED=true on
          Vercel to reveal it; default-off keeps a non-functional block out of
          prod, matching the backend's build-to-activate discipline. */}
      {process.env.NEXT_PUBLIC_OTP_ENABLED === "true" ? (
        <AlreadyMember tenantId={tenantId} />
      ) : null}
    </div>
  );
}

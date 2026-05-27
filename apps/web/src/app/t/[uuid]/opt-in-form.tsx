"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { useForm } from "react-hook-form";

import { type CustomerIdentify, customerIdentifySchema } from "@smarttap/core";

import { optInAction } from "./actions";

const CONSENT_TEXT =
  "I agree to receive offers and updates from this business via SMS or WhatsApp. " +
  "I can ask to be removed at any time.";

interface Props {
  tenantId: string;
  tenantName: string;
  accentColor: string;
}

/**
 * Secondary CTA on /t/[uuid] — opt-in for the loyalty card.
 *
 * Visual treatment is intentionally subordinate to the Review button
 * above: white card, smaller heading, no shadow, sits below the fold.
 * Returning (opted-in) customers don't see this at all — TapView only
 * renders the form when `customer === null`.
 */
export function OptInForm({ tenantId, tenantName, accentColor }: Props) {
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
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="flex w-full flex-col gap-3 rounded-2xl bg-white/95 p-4 text-left text-brand-black"
    >
      <header className="flex flex-col gap-0.5">
        <p className="font-display text-base leading-tight">
          Keep your stamps in your pocket
        </p>
        <p className="text-xs text-muted-foreground">
          Join {tenantName}&apos;s loyalty card — 1 tap, no app.
        </p>
      </header>

      <input type="hidden" {...register("tenant_id")} />
      <input type="hidden" {...register("gdpr_consent_text")} />

      <label className="flex flex-col gap-1 text-sm">
        <span className="sr-only">Phone (Irish)</span>
        <input
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="+353 86 123 4567"
          {...register("phone")}
          className="rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
        {errors.phone ? (
          <span className="text-xs text-red-600">{errors.phone.message}</span>
        ) : null}
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="sr-only">Name (optional)</span>
        <input
          type="text"
          autoComplete="given-name"
          placeholder="Name (optional)"
          {...register("name")}
          className="rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
        {errors.name ? (
          <span className="text-xs text-red-600">{errors.name.message}</span>
        ) : null}
      </label>

      <label className="flex items-start gap-2 text-[11px] leading-snug">
        <input
          type="checkbox"
          {...register("gdpr_consent")}
          className="mt-0.5"
        />
        <span>
          I agree to receive offers from <strong>{tenantName}</strong> via SMS
          or WhatsApp. I can ask to be removed at any time.
        </span>
      </label>
      {errors.gdpr_consent ? (
        <span className="text-xs text-red-600">{errors.gdpr_consent.message}</span>
      ) : null}

      {serverError ? <p className="text-sm text-red-600">{serverError}</p> : null}

      <button
        type="submit"
        disabled={isPending}
        className="mt-1 rounded-full px-4 py-2.5 text-sm font-semibold disabled:opacity-60"
        style={{ backgroundColor: accentColor, color: "#1A1A1A" }}
      >
        {isPending ? "Saving…" : "Join loyalty"}
      </button>
    </form>
  );
}

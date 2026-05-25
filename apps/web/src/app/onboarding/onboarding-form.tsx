"use client";

import { type FormEvent, useState, useTransition } from "react";

import { completeOnboardingAction } from "./actions";

interface Props {
  initialName: string;
}

const BUSINESS_TYPES: Array<{ value: string; label: string; sub: string }> = [
  { value: "barbershop", label: "Barbershop", sub: "Cuts, shaves" },
  { value: "cafe", label: "Café", sub: "Coffee, brunch" },
  { value: "pet_grooming", label: "Pet grooming", sub: "Dogs, cats" },
  { value: "salon", label: "Salon", sub: "Hair, beauty" },
  { value: "tattoo", label: "Tattoo studio", sub: "Ink work" },
  { value: "other", label: "Something else", sub: "We'll catch up" },
];

export function OnboardingForm({ initialName }: Props) {
  const [pending, startTransition] = useTransition();
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [topError, setTopError] = useState<string | null>(null);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const payload = {
      business_name: String(fd.get("business_name") ?? ""),
      business_type: String(fd.get("business_type") ?? "other") as
        | "barbershop"
        | "cafe"
        | "pet_grooming"
        | "salon"
        | "tattoo"
        | "other",
      google_review_url: String(fd.get("google_review_url") ?? "") || null,
      stamps_for_reward: Number(fd.get("stamps_for_reward")),
      reward_description: String(fd.get("reward_description") ?? ""),
      reward_expires_days: Number(fd.get("reward_expires_days")),
      stamp_rate_limit_minutes: Number(fd.get("stamp_rate_limit_minutes")),
    };
    setErrors({});
    setTopError(null);
    startTransition(async () => {
      const result = await completeOnboardingAction(payload);
      if (result && !result.ok) {
        setTopError(result.message);
        setErrors(result.fieldErrors ?? {});
      }
      // On success the action redirects; nothing more to do here.
    });
  }

  return (
    <form onSubmit={onSubmit} className="space-y-8">
      <Section step={1} title="Your business">
        <Field label="Business name" error={errors.business_name}>
          <input
            type="text"
            name="business_name"
            defaultValue={initialName}
            placeholder="ACME Barber"
            minLength={2}
            maxLength={80}
            required
            autoFocus
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>

        <fieldset className="space-y-1.5">
          <legend className="text-sm font-semibold">What kind of business?</legend>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {BUSINESS_TYPES.map((t, i) => (
              <label
                key={t.value}
                className="flex cursor-pointer items-center gap-3 rounded-lg border border-brand-black/15 p-3 transition hover:border-brand-green has-[:checked]:border-brand-green has-[:checked]:bg-brand-green/5"
              >
                <input
                  type="radio"
                  name="business_type"
                  value={t.value}
                  defaultChecked={i === 0}
                  className="h-4 w-4 accent-brand-green"
                />
                <span>
                  <span className="block font-semibold">{t.label}</span>
                  <span className="block text-xs text-brand-black/60">{t.sub}</span>
                </span>
              </label>
            ))}
          </div>
          {errors.business_type ? (
            <p className="text-xs text-red-600">{errors.business_type}</p>
          ) : null}
        </fieldset>
      </Section>

      <Section step={2} title="Google reviews" optional>
        <Field
          label="Google review URL"
          hint="Paste the direct 'write a review' link. You can add this later."
          error={errors.google_review_url}
        >
          <input
            type="url"
            name="google_review_url"
            placeholder="https://g.page/r/..."
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>
      </Section>

      <Section step={3} title="Your first reward">
        <Field
          label="Stamps needed"
          hint="Most barbershops start with 8."
          error={errors.stamps_for_reward}
          suffix="stamps"
        >
          <input
            type="number"
            name="stamps_for_reward"
            defaultValue={8}
            min={1}
            max={50}
            required
            className="w-28 rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>

        <Field
          label="What do they get?"
          hint="The customer sees this on the stamp screen."
          error={errors.reward_description}
        >
          <input
            type="text"
            name="reward_description"
            placeholder="Free haircut"
            minLength={2}
            maxLength={120}
            required
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field
            label="Reward expires after"
            error={errors.reward_expires_days}
            suffix="days"
          >
            <input
              type="number"
              name="reward_expires_days"
              defaultValue={30}
              min={1}
              max={365}
              required
              className="w-24 rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
            />
          </Field>
          <Field
            label="Time between stamps"
            hint="Anti-fraud cooldown per customer."
            error={errors.stamp_rate_limit_minutes}
            suffix="min"
          >
            <input
              type="number"
              name="stamp_rate_limit_minutes"
              defaultValue={120}
              min={0}
              max={1440}
              required
              className="w-24 rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
            />
          </Field>
        </div>
      </Section>

      {topError ? (
        <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {topError}
        </div>
      ) : null}

      <div className="flex items-center justify-end">
        <button
          type="submit"
          disabled={pending}
          className="rounded-full bg-brand-green px-8 py-3 font-semibold text-brand-off-white disabled:opacity-60"
        >
          {pending ? "Finishing…" : "Finish setup"}
        </button>
      </div>
    </form>
  );
}

function Section({
  step,
  title,
  optional,
  children,
}: {
  step: number;
  title: string;
  optional?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4 rounded-2xl border border-brand-black/10 bg-white p-6 shadow-sm">
      <div className="flex items-baseline gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-green text-sm font-semibold text-brand-off-white">
          {step}
        </span>
        <h2 className="font-display text-xl">{title}</h2>
        {optional ? (
          <span className="text-xs uppercase tracking-wide text-brand-black/50">
            Optional
          </span>
        ) : null}
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Field({
  label,
  hint,
  error,
  suffix,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  suffix?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-semibold">{label}</label>
      <div className="flex items-center gap-2">
        {children}
        {suffix ? <span className="text-sm text-brand-black/60">{suffix}</span> : null}
      </div>
      {error ? (
        <p className="text-xs text-red-600">{error}</p>
      ) : hint ? (
        <p className="text-xs text-brand-black/55">{hint}</p>
      ) : null}
    </div>
  );
}

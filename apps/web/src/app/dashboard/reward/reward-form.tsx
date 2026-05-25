"use client";

import { type FormEvent, useState, useTransition } from "react";

import { saveRewardConfigAction } from "./actions";

export interface RewardFormInitial {
  stamps_for_reward: number;
  reward_description: string;
  reward_expires_days: number;
  stamp_rate_limit_minutes: number;
}

interface Props {
  initial: RewardFormInitial;
}

type Banner =
  | { kind: "success"; text: string }
  | { kind: "error"; text: string }
  | null;

export function RewardForm({ initial }: Props) {
  const [pending, startTransition] = useTransition();
  const [banner, setBanner] = useState<Banner>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const payload = {
      stamps_for_reward: Number(fd.get("stamps_for_reward")),
      reward_description: String(fd.get("reward_description") ?? ""),
      reward_expires_days: Number(fd.get("reward_expires_days")),
      stamp_rate_limit_minutes: Number(fd.get("stamp_rate_limit_minutes")),
    };
    setBanner(null);
    setFieldErrors({});
    startTransition(async () => {
      const result = await saveRewardConfigAction(payload);
      if (result.ok) {
        setBanner({ kind: "success", text: "Saved." });
      } else {
        setBanner({ kind: "error", text: result.message });
        setFieldErrors(result.fieldErrors ?? {});
      }
    });
  }

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-6 rounded-2xl border border-brand-black/10 bg-white p-6 shadow-sm"
    >
      <Field
        name="stamps_for_reward"
        label="Stamps needed for a reward"
        hint="Most barbershops use 8 to 12."
        error={fieldErrors.stamps_for_reward}
      >
        <input
          type="number"
          name="stamps_for_reward"
          defaultValue={initial.stamps_for_reward || 10}
          min={1}
          max={50}
          required
          className="w-32 rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
      </Field>

      <Field
        name="reward_description"
        label="What do they get?"
        hint="Shown to the customer on the stamp screen."
        error={fieldErrors.reward_description}
      >
        <input
          type="text"
          name="reward_description"
          defaultValue={initial.reward_description}
          placeholder="Free haircut"
          minLength={2}
          maxLength={120}
          required
          className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
      </Field>

      <Field
        name="reward_expires_days"
        label="Reward expires after"
        hint="Days the customer has to redeem after earning the reward."
        error={fieldErrors.reward_expires_days}
        suffix="days"
      >
        <input
          type="number"
          name="reward_expires_days"
          defaultValue={initial.reward_expires_days || 30}
          min={1}
          max={365}
          required
          className="w-32 rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
      </Field>

      <Field
        name="stamp_rate_limit_minutes"
        label="Time between stamps for the same customer"
        hint="Stops repeat taps from gaming the system. 0 means no limit."
        error={fieldErrors.stamp_rate_limit_minutes}
        suffix="minutes"
      >
        <input
          type="number"
          name="stamp_rate_limit_minutes"
          defaultValue={initial.stamp_rate_limit_minutes}
          min={0}
          max={1440}
          required
          className="w-32 rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
        />
      </Field>

      {banner ? (
        <div
          role="status"
          className={`rounded-lg px-3 py-2 text-sm ${
            banner.kind === "success"
              ? "bg-brand-green/10 text-brand-green"
              : "bg-red-50 text-red-700"
          }`}
        >
          {banner.text}
        </div>
      ) : null}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-full bg-brand-green px-6 py-2.5 text-sm font-semibold text-brand-off-white disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}

function Field({
  label,
  hint,
  error,
  suffix,
  children,
}: {
  name: string;
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

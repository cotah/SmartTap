"use client";

import { Calendar, Gift, Hash, Timer, type LucideIcon } from "lucide-react";
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
      className="space-y-8 rounded-xl border border-brand-green/5 bg-white p-6 shadow-[0_4px_24px_rgba(27,77,62,0.04)] md:p-8"
    >
      {/* Section: Basic details */}
      <section className="space-y-5">
        <h2 className="border-b border-neutral-300/30 pb-2 text-xs font-bold uppercase tracking-widest text-brand-green">
          Basic details
        </h2>

        <Field
          label="What do they get?"
          hint="Shown to the customer on the stamp screen."
          error={fieldErrors.reward_description}
        >
          <IconInput icon={Gift}>
            <input
              type="text"
              name="reward_description"
              defaultValue={initial.reward_description}
              placeholder="Free haircut"
              minLength={2}
              maxLength={120}
              required
              className={INPUT_CLASS}
            />
          </IconInput>
        </Field>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <Field
            label="Stamps needed"
            hint="Most barbershops use 8 to 12."
            error={fieldErrors.stamps_for_reward}
          >
            <IconInput icon={Hash}>
              <input
                type="number"
                name="stamps_for_reward"
                defaultValue={initial.stamps_for_reward || 10}
                min={1}
                max={50}
                required
                className={INPUT_CLASS}
              />
            </IconInput>
          </Field>

          <Field
            label="Expiry (days)"
            hint="How long customers have to redeem."
            error={fieldErrors.reward_expires_days}
          >
            <IconInput icon={Calendar}>
              <input
                type="number"
                name="reward_expires_days"
                defaultValue={initial.reward_expires_days || 30}
                min={1}
                max={365}
                required
                className={INPUT_CLASS}
              />
            </IconInput>
          </Field>
        </div>
      </section>

      {/* Section: Rules & limits */}
      <section className="space-y-5">
        <h2 className="border-b border-neutral-300/30 pb-2 text-xs font-bold uppercase tracking-widest text-brand-green">
          Rules &amp; limits
        </h2>

        <Field
          label="Tap cooldown (minutes)"
          hint="Stops repeat taps from gaming the system. 0 means no limit."
          error={fieldErrors.stamp_rate_limit_minutes}
        >
          <IconInput icon={Timer}>
            <input
              type="number"
              name="stamp_rate_limit_minutes"
              defaultValue={initial.stamp_rate_limit_minutes}
              min={0}
              max={1440}
              required
              className={INPUT_CLASS}
            />
          </IconInput>
        </Field>
      </section>

      {banner ? (
        <div
          role="status"
          className={`rounded-lg px-4 py-3 text-sm ${
            banner.kind === "success"
              ? "bg-brand-green/10 text-brand-green"
              : "bg-red-50 text-red-700"
          }`}
        >
          {banner.text}
        </div>
      ) : null}

      <div className="flex items-center justify-end gap-3 border-t border-neutral-300/30 pt-6">
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-brand-green px-6 py-3 text-sm font-bold uppercase tracking-wider text-white shadow-sm transition-colors hover:bg-green-800 disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}

const INPUT_CLASS =
  "block w-full rounded-lg border border-neutral-300/40 bg-brand-off-white py-3 pl-11 pr-4 text-base text-brand-black shadow-[inset_0_2px_4px_rgba(27,77,62,0.04)] outline-none transition-colors placeholder:text-neutral-600/40 focus:border-brand-amber focus:ring-2 focus:ring-brand-amber/30";

function IconInput({
  icon: Icon,
  children,
}: {
  icon: LucideIcon;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-neutral-600">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </span>
      {children}
    </div>
  );
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <label className="block text-xs font-bold uppercase tracking-wider text-brand-black">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-xs text-red-600">{error}</p>
      ) : hint ? (
        <p className="text-xs text-neutral-600">{hint}</p>
      ) : null}
    </div>
  );
}

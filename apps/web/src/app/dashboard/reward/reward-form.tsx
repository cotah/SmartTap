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
      className="space-y-8 rounded-xl border border-electric-border bg-electric-surface p-6 shadow-[0_4px_24px_rgba(0,0,0,0.04)] md:p-8"
    >
      {/* Section: Basic details */}
      <section className="space-y-5">
        <h2 className="border-b border-electric-border pb-2 text-xs font-bold uppercase tracking-widest text-electric-cyan">
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
        <h2 className="border-b border-electric-border pb-2 text-xs font-bold uppercase tracking-widest text-electric-cyan">
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
              ? "bg-electric-cyan/10 text-electric-cyan"
              : "bg-red-500/10 text-red-300"
          }`}
        >
          {banner.text}
        </div>
      ) : null}

      <div className="flex items-center justify-end gap-3 border-t border-electric-border pt-6">
        <button
          type="submit"
          disabled={pending}
          className="rounded-lg bg-electric-cyan px-6 py-3 text-sm font-bold uppercase tracking-wider text-electric-bg shadow-sm transition-colors hover:bg-electric-cyan-deep disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}

const INPUT_CLASS =
  "block w-full rounded-lg border border-electric-border bg-electric-surface-2 py-3 pl-11 pr-4 text-base text-electric-text shadow-[inset_0_2px_4px_rgba(0,0,0,0.04)] outline-none transition-colors placeholder:text-electric-text-muted focus:border-electric-cyan focus:ring-2 focus:ring-electric-cyan/30";

function IconInput({
  icon: Icon,
  children,
}: {
  icon: LucideIcon;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-electric-text-muted">
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
      <label className="block text-xs font-bold uppercase tracking-wider text-electric-text">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-xs text-red-300">{error}</p>
      ) : hint ? (
        <p className="text-xs text-electric-text-muted">{hint}</p>
      ) : null}
    </div>
  );
}

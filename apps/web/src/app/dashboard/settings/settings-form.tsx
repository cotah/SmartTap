"use client";

import { Globe, Link as LinkIcon, type LucideIcon, MapPin, Store } from "lucide-react";
import { type FormEvent, useState, useTransition } from "react";

import { saveSettingsAction } from "./actions";

export interface SettingsFormInitial {
  name: string;
  primary_color: string;
  accent_color: string;
  logo_url: string;
  google_review_url: string;
  google_business_url: string;
  google_place_id: string;
}

interface Props {
  initial: SettingsFormInitial;
}

type Banner =
  | { kind: "success"; text: string }
  | { kind: "error"; text: string }
  | null;

export function SettingsForm({ initial }: Props) {
  const [pending, startTransition] = useTransition();
  const [banner, setBanner] = useState<Banner>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const payload = {
      name: String(fd.get("name") ?? ""),
      primary_color: String(fd.get("primary_color") ?? ""),
      accent_color: String(fd.get("accent_color") ?? ""),
      logo_url: String(fd.get("logo_url") ?? ""),
      google_review_url: String(fd.get("google_review_url") ?? ""),
      google_business_url: String(fd.get("google_business_url") ?? ""),
      google_place_id: String(fd.get("google_place_id") ?? ""),
    };
    setBanner(null);
    setErrors({});
    startTransition(async () => {
      const result = await saveSettingsAction(payload);
      if (result.ok) {
        setBanner({ kind: "success", text: "Saved." });
      } else {
        setBanner({ kind: "error", text: result.message });
        setErrors(result.fieldErrors ?? {});
      }
    });
  }

  return (
    <form onSubmit={onSubmit} className="space-y-8">
      <Section
        title="Brand identity"
        subtitle="This information appears on your customer-facing loyalty card."
        icon={Store}
      >
        <Field label="Business name" error={errors.name}>
          <input
            type="text"
            name="name"
            defaultValue={initial.name}
            minLength={2}
            maxLength={80}
            required
            className={INPUT_CLASS}
          />
        </Field>

        <Field
          label="Logo URL"
          hint="Public image URL. Leave empty to show the SmartTap default."
          error={errors.logo_url}
        >
          <IconInput icon={LinkIcon}>
            <input
              type="url"
              name="logo_url"
              defaultValue={initial.logo_url}
              placeholder="https://…"
              className={INPUT_CLASS_WITH_ICON}
            />
          </IconInput>
        </Field>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Primary color" error={errors.primary_color}>
            <ColorInput name="primary_color" initial={initial.primary_color} />
          </Field>
          <Field label="Accent color" error={errors.accent_color}>
            <ColorInput name="accent_color" initial={initial.accent_color} />
          </Field>
        </div>
      </Section>

      <Section
        title="Google integration"
        subtitle="Where customers land when they tap the review button."
        icon={Globe}
      >
        <Field
          label="Google review URL"
          hint="The direct write-a-review link from your Google Business profile."
          error={errors.google_review_url}
        >
          <IconInput icon={LinkIcon}>
            <input
              type="url"
              name="google_review_url"
              defaultValue={initial.google_review_url}
              placeholder="https://g.page/r/…"
              className={INPUT_CLASS_WITH_ICON}
            />
          </IconInput>
        </Field>

        <Field label="Google business URL" error={errors.google_business_url}>
          <IconInput icon={LinkIcon}>
            <input
              type="url"
              name="google_business_url"
              defaultValue={initial.google_business_url}
              placeholder="https://maps.google.com/…"
              className={INPUT_CLASS_WITH_ICON}
            />
          </IconInput>
        </Field>

        <Field
          label="Google Place ID"
          hint="Optional. Used by future review monitoring features."
        >
          <IconInput icon={MapPin}>
            <input
              type="text"
              name="google_place_id"
              defaultValue={initial.google_place_id}
              placeholder="ChIJ…"
              className={`${INPUT_CLASS_WITH_ICON} font-mono text-sm`}
            />
          </IconInput>
        </Field>
      </Section>

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

      <div className="flex items-center justify-end gap-3">
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
  "block w-full rounded-lg border border-electric-border bg-electric-surface-2 px-4 py-3 text-base text-electric-text shadow-[inset_0_2px_4px_rgba(0,0,0,0.04)] outline-none transition-colors placeholder:text-electric-text-muted focus:border-electric-cyan focus:ring-2 focus:ring-electric-cyan/30";

const INPUT_CLASS_WITH_ICON =
  "block w-full rounded-lg border border-electric-border bg-electric-surface-2 py-3 pl-11 pr-4 text-base text-electric-text shadow-[inset_0_2px_4px_rgba(0,0,0,0.04)] outline-none transition-colors placeholder:text-electric-text-muted focus:border-electric-cyan focus:ring-2 focus:ring-electric-cyan/30";

function Section({
  title,
  subtitle,
  icon: Icon,
  children,
}: {
  title: string;
  subtitle?: string;
  icon: LucideIcon;
  children: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-electric-border bg-electric-surface shadow-[0_4px_24px_rgba(0,0,0,0.04)]">
      <div className="flex items-center gap-4 border-b border-electric-border p-6 md:p-8">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-electric-surface-2 text-electric-cyan">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <h2 className="font-display text-xl text-electric-cyan">{title}</h2>
          {subtitle ? (
            <p className="mt-1 text-sm text-electric-text-muted">{subtitle}</p>
          ) : null}
        </div>
      </div>
      <div className="space-y-5 p-6 md:p-8">{children}</div>
    </section>
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

function ColorInput({ name, initial }: { name: string; initial: string }) {
  const [value, setValue] = useState(initial);
  return (
    <div className="flex items-center gap-3 rounded-lg border border-electric-border bg-electric-surface p-3">
      <input
        type="color"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="h-12 w-12 shrink-0 cursor-pointer rounded-full border-2 border-white shadow-md"
        aria-label={`${name} color picker`}
      />
      <input
        type="text"
        name={name}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        pattern="^#[0-9A-Fa-f]{6}$"
        maxLength={7}
        required
        className="w-full rounded-lg border border-electric-border bg-electric-surface-2 px-3 py-2 font-mono text-sm uppercase text-electric-text shadow-[inset_0_2px_4px_rgba(0,0,0,0.04)] outline-none focus:border-electric-cyan focus:ring-2 focus:ring-electric-cyan/30"
      />
    </div>
  );
}

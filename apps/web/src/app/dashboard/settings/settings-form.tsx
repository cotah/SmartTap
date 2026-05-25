"use client";

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
      <Section title="Brand" subtitle="Shown on the customer tap screen.">
        <Field label="Business name" error={errors.name}>
          <input
            type="text"
            name="name"
            defaultValue={initial.name}
            minLength={2}
            maxLength={80}
            required
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>

        <Field
          label="Logo URL"
          hint="Public image URL. Leave empty to use the SmartTap default."
          error={errors.logo_url}
        >
          <input
            type="url"
            name="logo_url"
            defaultValue={initial.logo_url}
            placeholder="https://..."
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
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
        title="Google"
        subtitle="Where the customer goes when they tap the review button."
      >
        <Field
          label="Google review URL"
          hint="The direct write-a-review link from your Google Business profile."
          error={errors.google_review_url}
        >
          <input
            type="url"
            name="google_review_url"
            defaultValue={initial.google_review_url}
            placeholder="https://g.page/r/..."
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>

        <Field label="Google business URL" error={errors.google_business_url}>
          <input
            type="url"
            name="google_business_url"
            defaultValue={initial.google_business_url}
            placeholder="https://maps.google.com/..."
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>

        <Field
          label="Google Place ID"
          hint="Optional. Used by future review monitoring features."
        >
          <input
            type="text"
            name="google_place_id"
            defaultValue={initial.google_place_id}
            placeholder="ChIJ..."
            className="w-full rounded-lg border border-brand-black/20 px-3 py-2 outline-none focus:border-brand-green"
          />
        </Field>
      </Section>

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

      <div>
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

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4 rounded-2xl border border-brand-black/10 bg-white p-6 shadow-sm">
      <div>
        <h2 className="font-display text-xl">{title}</h2>
        {subtitle ? <p className="text-sm text-brand-black/60">{subtitle}</p> : null}
      </div>
      <div className="space-y-4">{children}</div>
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
    <div className="space-y-1.5">
      <label className="block text-sm font-semibold">{label}</label>
      {children}
      {error ? (
        <p className="text-xs text-red-600">{error}</p>
      ) : hint ? (
        <p className="text-xs text-brand-black/55">{hint}</p>
      ) : null}
    </div>
  );
}

function ColorInput({ name, initial }: { name: string; initial: string }) {
  const [value, setValue] = useState(initial);
  return (
    <div className="flex items-center gap-2">
      <input
        type="color"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="h-10 w-12 cursor-pointer rounded-lg border border-brand-black/20"
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
        className="w-32 rounded-lg border border-brand-black/20 px-3 py-2 font-mono text-sm uppercase outline-none focus:border-brand-green"
      />
    </div>
  );
}

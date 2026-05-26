"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { NfcTagColor, NfcTagFormat } from "@/lib/api";

import {
  createTagAction,
  toggleTagActiveAction,
  updateTagAction,
  type TagActionResult,
} from "./actions";
import {
  COLOR_LABELS,
  COLOR_OPTIONS,
  COLOR_SWATCH,
  FORMAT_LABELS,
  FORMAT_OPTIONS,
} from "./tag-labels";

type Mode = "create" | "edit";

interface Props {
  mode: Mode;
  // Set only on edit — drives initial values, edit/toggle paths, and the
  // public URL display.
  tagId?: string;
  tagUuid?: string;
  initialFormat?: NfcTagFormat;
  initialColor?: NfcTagColor;
  initialLocationName?: string;
  initialIsActive?: boolean;
  // Set so the form can show "https://smarttap.ie/t/<uuid>" — pulled from
  // env at the page level so this component stays env-agnostic.
  siteUrl: string;
}

export function TagForm({
  mode,
  tagId,
  tagUuid,
  initialFormat = "counter_stand",
  initialColor = "black",
  initialLocationName = "",
  initialIsActive = true,
  siteUrl,
}: Props) {
  const router = useRouter();
  const [format, setFormat] = useState<NfcTagFormat>(initialFormat);
  const [color, setColor] = useState<NfcTagColor>(initialColor);
  const [locationName, setLocationName] = useState(initialLocationName);
  const [isActive, setIsActive] = useState(initialIsActive);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, startSave] = useTransition();
  const [toggling, startToggle] = useTransition();
  const [copied, setCopied] = useState(false);

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    startSave(async () => {
      const input = { format, color, location_name: locationName };
      const result: TagActionResult =
        mode === "create"
          ? await createTagAction(input)
          : await updateTagAction(tagId!, input);
      if (!result.ok) {
        setError(result.message);
        setFieldErrors(result.fieldErrors ?? {});
        return;
      }
      router.push("/dashboard/tags");
      router.refresh();
    });
  }

  function onToggle() {
    if (!tagId) return;
    setError(null);
    const next = !isActive;
    startToggle(async () => {
      const result = await toggleTagActiveAction(tagId, next);
      if (!result.ok) {
        setError(result.message);
        return;
      }
      setIsActive(next);
      router.refresh();
    });
  }

  async function onCopyUrl() {
    if (!tagUuid) return;
    const url = `${siteUrl}/t/${tagUuid}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      // Reset the affordance after 2s so the merchant can copy again.
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Older browsers / iframes without permission — fall back to manual.
      window.prompt("Copy this URL:", url);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <Section title="Format">
        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as NfcTagFormat)}
          className="w-full rounded-xl border border-brand-black/15 bg-white px-3 py-2 text-sm"
        >
          {FORMAT_OPTIONS.map((f) => (
            <option key={f} value={f}>
              {FORMAT_LABELS[f]}
            </option>
          ))}
        </select>
        {fieldErrors.format ? (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.format}</p>
        ) : null}
      </Section>

      <Section title="Colour" hint="Limited to PLA filament we keep in stock.">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          {COLOR_OPTIONS.map((c) => {
            const selected = c === color;
            return (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`flex items-center gap-2 rounded-xl border bg-white p-2 text-left text-xs transition ${
                  selected
                    ? "border-brand-green ring-2 ring-brand-green/30"
                    : "border-brand-black/15 hover:border-brand-black/40"
                }`}
              >
                <span
                  className="inline-block h-5 w-5 rounded-full border border-brand-black/10"
                  style={{ backgroundColor: COLOR_SWATCH[c] }}
                  aria-hidden
                />
                <span>{COLOR_LABELS[c]}</span>
              </button>
            );
          })}
        </div>
        {fieldErrors.color ? (
          <p className="mt-1 text-xs text-red-600">{fieldErrors.color}</p>
        ) : null}
      </Section>

      <Section
        title="Location"
        hint='Optional. e.g. "Front desk", "Bar", "Reception".'
      >
        <input
          type="text"
          value={locationName}
          onChange={(e) => setLocationName(e.target.value)}
          maxLength={80}
          placeholder="(optional)"
          className={`w-full rounded-xl border bg-white px-3 py-2 text-sm ${
            fieldErrors.location_name ? "border-red-400" : "border-brand-black/15"
          }`}
        />
        {fieldErrors.location_name ? (
          <p className="mt-1 text-xs text-red-600">
            {fieldErrors.location_name}
          </p>
        ) : null}
      </Section>

      {/* Edit-only blocks: public URL + activate toggle. Both rely on
          tagId/tagUuid which only exist after creation. */}
      {mode === "edit" && tagUuid ? (
        <>
          <Section
            title="Public URL"
            hint="Write this URL to the physical NFC tag using TagWriter (or any NFC-writing app). Same URL also works as a QR code target."
          >
            <div className="flex items-center gap-2 rounded-xl border border-brand-black/15 bg-brand-off-white/40 px-3 py-2 text-sm">
              <code className="flex-1 truncate font-mono text-xs">
                {siteUrl}/t/{tagUuid}
              </code>
              <button
                type="button"
                onClick={onCopyUrl}
                className="rounded-full border border-brand-black/20 px-3 py-1 text-xs font-semibold hover:border-brand-green"
              >
                {copied ? "Copied ✓" : "Copy"}
              </button>
            </div>
          </Section>

          <Section title="Status">
            <div className="flex items-center justify-between rounded-xl border border-brand-black/10 bg-white px-3 py-2 text-sm">
              <div>
                <p className="font-medium">
                  {isActive ? "Active" : "Inactive"}
                </p>
                <p className="text-xs text-brand-black/60">
                  {isActive
                    ? "Customers tapping this tag earn stamps."
                    : "Tap requests are rejected. Tap history is preserved."}
                </p>
              </div>
              <button
                type="button"
                onClick={onToggle}
                disabled={toggling}
                className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                  isActive
                    ? "border border-brand-black/20 hover:border-red-400"
                    : "bg-brand-green text-brand-off-white"
                } disabled:opacity-60`}
              >
                {toggling
                  ? "Saving…"
                  : isActive
                    ? "Deactivate"
                    : "Activate"}
              </button>
            </div>
          </Section>
        </>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <div className="flex flex-wrap gap-2 border-t border-brand-black/10 pt-4">
        <button
          type="submit"
          disabled={saving}
          className="rounded-full bg-brand-green px-5 py-2 text-sm font-semibold text-brand-off-white disabled:opacity-60"
        >
          {saving
            ? "Saving…"
            : mode === "create"
              ? "Create tag"
              : "Save changes"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/dashboard/tags")}
          className="rounded-full border border-brand-black/20 px-5 py-2 text-sm font-semibold"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-black/70">
          {title}
        </p>
        {hint ? <p className="text-xs text-brand-black/50">{hint}</p> : null}
      </div>
      {children}
    </section>
  );
}

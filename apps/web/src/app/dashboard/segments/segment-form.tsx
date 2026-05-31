"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { SegmentCriteria, SegmentPreview } from "@/lib/api";

import {
  createSegmentAction,
  deleteSegmentAction,
  previewUnsavedSegmentAction,
  updateSegmentAction,
  type SegmentActionResult,
} from "./actions";

type Mode = "create" | "edit";

interface Props {
  mode: Mode;
  // Only set in edit mode — drives initial values + which action runs on save.
  segmentId?: string;
  initialName?: string;
  initialCriteria?: SegmentCriteria;
}

/**
 * Shared form for /dashboard/segments/new and /dashboard/segments/[id].
 *
 * Design notes:
 * - Criteria stored as a single state blob so adding a new criterion later
 *   is one input + one field on SegmentCriteria. No per-field useState.
 * - Number inputs use empty string for "unset"; we map "" ↔ null at the
 *   boundary so the wire shape only sees number | null.
 * - Preview is opt-in via the "Preview" button to keep backend load
 *   predictable (vs. recomputing on every keystroke).
 */
export function SegmentForm({
  mode,
  segmentId,
  initialName = "",
  initialCriteria,
}: Props) {
  const router = useRouter();
  const [name, setName] = useState(initialName);
  const [criteria, setCriteria] = useState<SegmentCriteria>(initialCriteria ?? {});
  const [preview, setPreview] = useState<SegmentPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saving, startSave] = useTransition();
  const [previewing, startPreview] = useTransition();
  const [deleting, startDelete] = useTransition();
  const [confirmDelete, setConfirmDelete] = useState(false);

  function update<K extends keyof SegmentCriteria>(
    key: K,
    value: SegmentCriteria[K],
  ) {
    setCriteria((prev) => ({ ...prev, [key]: value }));
    setPreview(null); // any change invalidates the visible preview
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    startSave(async () => {
      const input = { name, criteria };
      const result: SegmentActionResult =
        mode === "create"
          ? await createSegmentAction(input)
          : await updateSegmentAction(segmentId!, input);
      if (!result.ok) {
        setError(result.message);
        setFieldErrors(result.fieldErrors ?? {});
        return;
      }
      router.push("/dashboard/segments");
      router.refresh();
    });
  }

  function onPreview() {
    setError(null);
    startPreview(async () => {
      const result = await previewUnsavedSegmentAction({ name, criteria });
      if (!result.ok) {
        setError(result.message);
        setPreview(null);
        return;
      }
      setPreview(result.preview);
    });
  }

  function onDelete() {
    if (!segmentId) return;
    setError(null);
    startDelete(async () => {
      const result = await deleteSegmentAction(segmentId);
      if (!result.ok) {
        setError(result.message);
        return;
      }
      router.push("/dashboard/segments");
      router.refresh();
    });
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <Section title="Name">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Loyal regulars"
          maxLength={80}
          className={`w-full rounded-xl border bg-electric-surface px-3 py-2 text-sm ${
            fieldErrors.name ? "border-red-400" : "border-electric-border"
          }`}
        />
        {fieldErrors.name ? (
          <p className="mt-1 text-xs text-red-300">{fieldErrors.name}</p>
        ) : null}
      </Section>

      <Section
        title="Visits"
        hint="Total lifetime visits (counted from the first tap)."
      >
        <RangeRow
          minLabel="Min visits"
          maxLabel="Max visits"
          minValue={criteria.visits_min ?? null}
          maxValue={criteria.visits_max ?? null}
          onMinChange={(v) => update("visits_min", v)}
          onMaxChange={(v) => update("visits_max", v)}
          maxError={fieldErrors.visits_max}
        />
      </Section>

      <Section title="Stamps" hint="Current stamp balance (resets at reward).">
        <RangeRow
          minLabel="Min stamps"
          maxLabel="Max stamps"
          minValue={criteria.stamps_min ?? null}
          maxValue={criteria.stamps_max ?? null}
          onMinChange={(v) => update("stamps_min", v)}
          onMaxChange={(v) => update("stamps_max", v)}
          maxError={fieldErrors.stamps_max}
        />
      </Section>

      <Section
        title="Recency"
        hint="Use one or both. Empty = no filter."
      >
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <DaysInput
            label="Visited in last (days)"
            value={criteria.last_visit_after_days ?? null}
            onChange={(v) => update("last_visit_after_days", v)}
          />
          <DaysInput
            label="No visit for at least (days)"
            value={criteria.last_visit_before_days ?? null}
            onChange={(v) => update("last_visit_before_days", v)}
          />
        </div>
      </Section>

      <Section title="Cohort" hint="Signed up within the last N days.">
        <DaysInput
          label="Signed up in last (days)"
          value={criteria.created_after_days ?? null}
          onChange={(v) => update("created_after_days", v)}
        />
      </Section>

      <Section title="Contact channels">
        <div className="space-y-2">
          <TriCheckbox
            label="Has email"
            value={criteria.has_email ?? null}
            onChange={(v) => update("has_email", v)}
          />
          <TriCheckbox
            label="Has phone"
            value={criteria.has_phone ?? null}
            onChange={(v) => update("has_phone", v)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={criteria.gdpr_consent_only === true}
              onChange={(e) =>
                update("gdpr_consent_only", e.target.checked ? true : null)
              }
            />
            <span>GDPR consent only (required for email/SMS sends)</span>
          </label>
        </div>
      </Section>

      {/* Preview panel */}
      <div className="rounded-2xl border border-electric-border bg-electric-surface-2/40 p-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold uppercase tracking-wide text-electric-text-muted">
            Preview
          </p>
          <button
            type="button"
            onClick={onPreview}
            disabled={previewing}
            className="rounded-full border border-electric-border px-4 py-1.5 text-sm font-semibold hover:border-electric-cyan disabled:opacity-60"
          >
            {previewing ? "Evaluating…" : "Run preview"}
          </button>
        </div>
        {preview ? (
          <PreviewBlock preview={preview} />
        ) : (
          <p className="mt-2 text-sm text-electric-text-muted">
            Click <strong>Run preview</strong> to see how many customers
            match. Doesn&apos;t save anything.
          </p>
        )}
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-electric-border pt-4">
        <div className="flex flex-wrap gap-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg disabled:opacity-60"
          >
            {saving ? "Saving…" : mode === "create" ? "Save segment" : "Save changes"}
          </button>
          <button
            type="button"
            onClick={() => router.push("/dashboard/segments")}
            className="rounded-full border border-electric-border px-5 py-2 text-sm font-semibold"
          >
            Cancel
          </button>
        </div>

        {mode === "edit" ? (
          <div className="flex items-center gap-2">
            {confirmDelete ? (
              <>
                <span className="text-xs text-electric-text-muted">Confirm?</span>
                <button
                  type="button"
                  onClick={onDelete}
                  disabled={deleting}
                  className="rounded-full bg-red-600 px-4 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                >
                  {deleting ? "Deleting…" : "Yes, delete"}
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmDelete(false)}
                  className="rounded-full border border-electric-border px-4 py-1.5 text-xs font-semibold"
                >
                  Keep
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setConfirmDelete(true)}
                className="text-xs font-semibold text-red-300 hover:underline"
              >
                Delete segment
              </button>
            )}
          </div>
        ) : null}
      </div>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

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
        <p className="text-sm font-semibold uppercase tracking-wide text-electric-text-muted">
          {title}
        </p>
        {hint ? (
          <p className="text-xs text-electric-text-muted">{hint}</p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

function RangeRow({
  minLabel,
  maxLabel,
  minValue,
  maxValue,
  onMinChange,
  onMaxChange,
  maxError,
}: {
  minLabel: string;
  maxLabel: string;
  minValue: number | null;
  maxValue: number | null;
  onMinChange: (v: number | null) => void;
  onMaxChange: (v: number | null) => void;
  maxError?: string;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      <NumberInput label={minLabel} value={minValue} onChange={onMinChange} />
      <div>
        <NumberInput label={maxLabel} value={maxValue} onChange={onMaxChange} />
        {maxError ? (
          <p className="mt-1 text-xs text-red-300">{maxError}</p>
        ) : null}
      </div>
    </div>
  );
}

function NumberInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-xs text-electric-text-muted">{label}</span>
      <input
        type="number"
        min={0}
        value={value ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") onChange(null);
          else {
            const n = Number(raw);
            onChange(Number.isFinite(n) && n >= 0 ? n : null);
          }
        }}
        className="rounded-xl border border-electric-border bg-electric-surface px-3 py-2 text-sm"
      />
    </label>
  );
}

function DaysInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-xs text-electric-text-muted">{label}</span>
      <input
        type="number"
        min={1}
        max={3650}
        value={value ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") onChange(null);
          else {
            const n = Number(raw);
            onChange(Number.isFinite(n) && n >= 1 ? n : null);
          }
        }}
        className="rounded-xl border border-electric-border bg-electric-surface px-3 py-2 text-sm"
      />
    </label>
  );
}

function TriCheckbox({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (v: boolean | null) => void;
}) {
  // Three-state radio set: ignore (null), must (true), must not (false).
  // Cleaner than a generic checkbox because the merchant has to make the
  // distinction explicit ("has phone" vs "doesn't have phone" are different
  // intents).
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <span className="min-w-[7rem]">{label}</span>
      <label className="flex items-center gap-1">
        <input
          type="radio"
          checked={value === null}
          onChange={() => onChange(null)}
        />
        <span className="text-xs">Ignore</span>
      </label>
      <label className="flex items-center gap-1">
        <input
          type="radio"
          checked={value === true}
          onChange={() => onChange(true)}
        />
        <span className="text-xs">Yes</span>
      </label>
      <label className="flex items-center gap-1">
        <input
          type="radio"
          checked={value === false}
          onChange={() => onChange(false)}
        />
        <span className="text-xs">No</span>
      </label>
    </div>
  );
}

function PreviewBlock({ preview }: { preview: SegmentPreview }) {
  const shown = preview.items.length;
  const more = preview.total - shown;
  return (
    <div className="mt-3 space-y-3">
      <p className="text-sm">
        <strong>{preview.total.toLocaleString()}</strong>{" "}
        {preview.total === 1 ? "customer matches" : "customers match"}.
        {more > 0 ? (
          <span className="text-electric-text-muted">
            {" "}Showing first {shown}.
          </span>
        ) : null}
      </p>
      {preview.items.length > 0 ? (
        <ul className="divide-y divide-electric-border rounded-xl border border-electric-border bg-electric-surface text-sm">
          {preview.items.map((c) => (
            <li key={c.id} className="flex items-center justify-between px-3 py-2">
              <div>
                <p className="font-medium">{c.name || "—"}</p>
                <p className="text-xs text-electric-text-muted">
                  {c.phone || c.email || "no contact"} ·{" "}
                  {c.total_visits} {c.total_visits === 1 ? "visit" : "visits"} ·{" "}
                  {c.current_stamps} stamps
                </p>
              </div>
              <span className="text-xs text-electric-text-muted">
                {c.last_visit_at
                  ? new Date(c.last_visit_at).toLocaleDateString("en-IE", {
                      day: "numeric",
                      month: "short",
                    })
                  : "never"}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-electric-text-muted">
          No customers match yet — try loosening the criteria.
        </p>
      )}
    </div>
  );
}

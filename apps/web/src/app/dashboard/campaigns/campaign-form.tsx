"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState, useTransition } from "react";

import { changeCampaignStatusAction, createCampaignAction, updateCampaignAction } from "./actions";

export interface CampaignFormInitial {
  id?: string;
  name: string;
  multiplier: number;
  starts_at: string; // datetime-local format: "YYYY-MM-DDTHH:mm"
  ends_at: string;
  status: "draft" | "active" | "paused" | "ended";
}

type Banner = { kind: "success" | "error"; text: string } | null;

interface Props {
  initial: CampaignFormInitial;
  mode: "create" | "edit";
}

export function CampaignForm({ initial, mode }: Props) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [banner, setBanner] = useState<Banner>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  // Edits are blocked server-side once a campaign is active. Surface that
  // here so the form is read-only with a clear explanation instead of letting
  // the user fill it out only to be rejected on submit.
  const editsLocked = mode === "edit" && initial.status !== "draft";

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fd = new FormData(event.currentTarget);
    const payload = {
      name: String(fd.get("name") ?? ""),
      multiplier: Number(fd.get("multiplier")),
      starts_at: toIso(String(fd.get("starts_at") ?? "")),
      ends_at: toIso(String(fd.get("ends_at") ?? "")),
      status: (fd.get("status") === "active" ? "active" : "draft") as
        | "draft"
        | "active",
    };
    setBanner(null);
    setFieldErrors({});
    startTransition(async () => {
      const result =
        mode === "create"
          ? await createCampaignAction(payload)
          : await updateCampaignAction(initial.id!, payload);
      if (result.ok) {
        router.push(`/dashboard/campaigns/${result.campaignId}`);
        return;
      }
      setBanner({ kind: "error", text: result.message });
      setFieldErrors(result.fieldErrors ?? {});
    });
  }

  function changeStatus(status: "active" | "paused" | "draft" | "ended") {
    if (!initial.id) return;
    setBanner(null);
    startTransition(async () => {
      const result = await changeCampaignStatusAction(initial.id!, status);
      if (result.ok) {
        router.refresh();
        setBanner({ kind: "success", text: `Status changed to ${status}.` });
      } else {
        setBanner({ kind: "error", text: result.message });
      }
    });
  }

  return (
    <div className="space-y-4">
      {editsLocked ? (
        <div
          role="status"
          className="rounded-lg border border-electric-cyan/30 bg-electric-cyan/15 px-3 py-2 text-sm text-electric-text"
        >
          This campaign is <strong>{initial.status}</strong>. Pause it to draft
          first if you want to edit its fields.
        </div>
      ) : null}

      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-2xl border border-electric-border bg-electric-surface p-6 shadow-sm"
      >
        <Field
          label="Campaign name"
          hint="Just for you. Customers don't see this."
          error={fieldErrors.name}
        >
          <input
            type="text"
            name="name"
            defaultValue={initial.name}
            placeholder="Weekend double stamps"
            minLength={2}
            maxLength={80}
            required
            disabled={editsLocked}
            className="w-full rounded-lg border border-electric-border px-3 py-2 outline-none focus:border-electric-cyan disabled:bg-electric-surface-2"
          />
        </Field>

        <Field
          label="Stamps multiplier"
          hint="How many stamps per visit during the campaign window. 2 is most common."
          error={fieldErrors.multiplier}
          suffix="×"
        >
          <select
            name="multiplier"
            defaultValue={String(initial.multiplier)}
            disabled={editsLocked}
            className="w-32 rounded-lg border border-electric-border px-3 py-2 outline-none focus:border-electric-cyan disabled:bg-electric-surface-2"
          >
            {[2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </Field>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field label="Starts" error={fieldErrors.starts_at}>
            <input
              type="datetime-local"
              name="starts_at"
              defaultValue={initial.starts_at}
              required
              disabled={editsLocked}
              className="w-full rounded-lg border border-electric-border px-3 py-2 outline-none focus:border-electric-cyan disabled:bg-electric-surface-2"
            />
          </Field>
          <Field label="Ends" error={fieldErrors.ends_at}>
            <input
              type="datetime-local"
              name="ends_at"
              defaultValue={initial.ends_at}
              required
              disabled={editsLocked}
              className="w-full rounded-lg border border-electric-border px-3 py-2 outline-none focus:border-electric-cyan disabled:bg-electric-surface-2"
            />
          </Field>
        </div>

        {mode === "create" ? (
          <Field
            label="When to start"
            hint="Draft lets you review before going live. Active goes live now."
          >
            <select
              name="status"
              defaultValue="draft"
              className="w-40 rounded-lg border border-electric-border px-3 py-2 outline-none focus:border-electric-cyan"
            >
              <option value="draft">Save as draft</option>
              <option value="active">Activate now</option>
            </select>
          </Field>
        ) : null}

        {banner ? (
          <div
            role="status"
            className={`rounded-lg px-3 py-2 text-sm ${
              banner.kind === "success"
                ? "bg-electric-cyan/10 text-electric-cyan"
                : "bg-red-500/10 text-red-300"
            }`}
          >
            {banner.text}
          </div>
        ) : null}

        {!editsLocked ? (
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={pending}
              className="rounded-full bg-electric-cyan px-6 py-2.5 text-sm font-semibold text-electric-bg disabled:opacity-60"
            >
              {pending ? "Saving…" : mode === "create" ? "Create campaign" : "Save changes"}
            </button>
          </div>
        ) : null}
      </form>

      {mode === "edit" && initial.id ? (
        <StatusControls
          status={initial.status}
          onChange={changeStatus}
          pending={pending}
        />
      ) : null}
    </div>
  );
}

function StatusControls({
  status,
  onChange,
  pending,
}: {
  status: CampaignFormInitial["status"];
  onChange: (s: "active" | "paused" | "draft" | "ended") => void;
  pending: boolean;
}) {
  const actions: { label: string; target: "active" | "paused" | "draft" | "ended" }[] = [];
  if (status === "draft") actions.push({ label: "Activate", target: "active" });
  if (status === "active") {
    actions.push({ label: "Pause", target: "paused" });
    actions.push({ label: "End campaign", target: "ended" });
  }
  if (status === "paused") {
    actions.push({ label: "Resume", target: "active" });
    actions.push({ label: "Back to draft", target: "draft" });
    actions.push({ label: "End campaign", target: "ended" });
  }
  if (actions.length === 0) return null;

  return (
    <div className="rounded-2xl border border-electric-border bg-electric-surface p-5 shadow-sm">
      <p className="text-sm font-semibold uppercase tracking-wide text-electric-text-muted">
        Status
      </p>
      <p className="mt-1 text-sm text-electric-text-muted">
        Currently <strong>{status}</strong>. {hint(status)}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {actions.map((a) => (
          <button
            key={a.target}
            type="button"
            onClick={() => onChange(a.target)}
            disabled={pending}
            className={`rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-wide disabled:opacity-60 ${
              a.target === "ended"
                ? "border border-red-500/30 bg-electric-surface text-red-300"
                : a.target === "active"
                  ? "bg-electric-cyan text-electric-bg"
                  : "border border-electric-border bg-electric-surface text-electric-text"
            }`}
          >
            {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function hint(status: CampaignFormInitial["status"]): string {
  switch (status) {
    case "draft":
      return "Activate when you're ready to start awarding extra stamps.";
    case "active":
      return "Stamps are being multiplied right now during the window.";
    case "paused":
      return "Multiplier is off. Resume to apply again, or back to draft to edit.";
    case "ended":
      return "Ended campaigns are read-only. Create a new one if you want to run a similar promo.";
  }
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
        {suffix ? <span className="text-sm text-electric-text-muted">{suffix}</span> : null}
      </div>
      {error ? (
        <p className="text-xs text-red-300">{error}</p>
      ) : hint ? (
        <p className="text-xs text-electric-text-muted">{hint}</p>
      ) : null}
    </div>
  );
}

// Converts the datetime-local string ("YYYY-MM-DDTHH:mm") to an ISO string
// with the browser's local TZ baked in, so the user sees the same time they
// picked when reading back the saved value.
function toIso(value: string): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString();
}

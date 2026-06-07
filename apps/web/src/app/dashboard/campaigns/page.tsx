import { Megaphone } from "lucide-react";
import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import type { Campaign } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

type CampaignKind = "live" | "scheduled" | "paused" | "ended";

const KIND_BADGE: Record<CampaignKind, { label: string; className: string }> = {
  live: { label: "Live", className: "bg-emerald-500/15 text-emerald-300" },
  scheduled: { label: "Scheduled", className: "bg-sky-500/15 text-sky-300" },
  paused: { label: "Paused", className: "bg-amber-500/15 text-amber-300" },
  ended: {
    label: "Ended",
    className: "bg-electric-surface-2 text-electric-text-muted",
  },
};

export default async function CampaignsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { items } = await api.listCampaigns();

  const counts = items.reduce(
    (acc, c) => {
      acc[classify(c)] += 1;
      return acc;
    },
    { live: 0, scheduled: 0, paused: 0, ended: 0 } as Record<CampaignKind, number>,
  );

  return (
    <main className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm text-electric-text-muted">
            <Link href="/dashboard" className="underline">
              Dashboard
            </Link>{" "}
            / Campaigns
          </p>
          <h1 className="font-display text-3xl">Campaigns</h1>
          <p className="mt-1 text-sm text-electric-text-muted">
            Run a double-stamp window to bring customers in faster.
          </p>
        </div>
        <Link
          href="/dashboard/campaigns/new"
          className="rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg transition-colors hover:bg-electric-cyan-deep"
        >
          New campaign
        </Link>
      </header>

      {items.length > 0 ? (
        <div className="flex flex-wrap gap-3">
          <SummaryStat label="Live now" value={counts.live} live={counts.live > 0} />
          <SummaryStat label="Scheduled" value={counts.scheduled} />
          {counts.paused > 0 ? (
            <SummaryStat label="Paused" value={counts.paused} />
          ) : null}
          <SummaryStat label="Ended" value={counts.ended} />
        </div>
      ) : null}

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((c) => (
            <li key={c.id}>
              <CampaignCard campaign={c} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function SummaryStat({
  label,
  value,
  live = false,
}: {
  label: string;
  value: number;
  live?: boolean;
}) {
  return (
    <div className="rounded-xl border border-electric-border bg-electric-surface px-4 py-3">
      <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-electric-text-muted">
        {live ? (
          <span
            className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400"
            aria-hidden="true"
          />
        ) : null}
        {label}
      </p>
      <p className="mt-1 font-display text-2xl font-semibold text-electric-text">
        {value.toLocaleString()}
      </p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-electric-border bg-electric-surface p-8 text-center">
      <p className="font-display text-lg">No campaigns yet</p>
      <p className="mt-1 text-sm text-electric-text-muted">
        Create a double-stamp window to reward extra visits during a slow
        period or a launch.
      </p>
      <Link
        href="/dashboard/campaigns/new"
        className="mt-4 inline-block rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg transition-colors hover:bg-electric-cyan-deep"
      >
        Create your first campaign
      </Link>
    </div>
  );
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  const kind = classify(campaign);
  const badge = KIND_BADGE[kind];

  return (
    <Link
      href={`/dashboard/campaigns/${campaign.id}`}
      className="flex h-full flex-col gap-3 rounded-2xl border border-electric-border bg-electric-surface p-4 transition hover:border-electric-cyan hover:bg-electric-surface-2"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-electric-cyan/15 text-electric-cyan">
            <Megaphone className="h-4 w-4" aria-hidden="true" />
          </span>
          <p className="truncate font-display text-lg">{campaign.name}</p>
        </div>
        <span
          className={`flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.className}`}
        >
          {kind === "live" ? (
            <span
              className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400"
              aria-hidden="true"
            />
          ) : null}
          {badge.label}
        </span>
      </div>
      <p className="text-sm text-electric-text-muted">
        <strong className="text-electric-cyan">{campaign.multiplier}× stamps</strong>{" "}
        · {formatRange(campaign)}
      </p>
    </Link>
  );
}

/** Bucket a campaign for the badge and summary strip. The backend never
 * auto-transitions, so an `active` campaign past its end date is treated as
 * ended, and one before its start as scheduled. */
function classify(c: Campaign): CampaignKind {
  if (c.status === "paused") return "paused";
  if (c.status === "ended") return "ended";
  if (c.status === "draft") return "scheduled";
  // active:
  const now = Date.now();
  const end = c.ends_at ? Date.parse(c.ends_at) : null;
  if (end != null && !Number.isNaN(end) && end < now) return "ended";
  const start = c.starts_at ? Date.parse(c.starts_at) : null;
  if (start != null && !Number.isNaN(start) && start > now) return "scheduled";
  return "live";
}

function formatRange(c: Campaign): string {
  const fmt = (iso: string | null) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-IE", { day: "numeric", month: "short" });
  };
  return `${fmt(c.starts_at)} → ${fmt(c.ends_at)}`;
}

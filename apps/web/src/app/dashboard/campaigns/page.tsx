import Link from "next/link";

import { getAuthApiClient } from "@/lib/api";
import type { Campaign } from "@/lib/api";
import { getDashboardContext } from "@/lib/dashboard-data";

export default async function CampaignsPage() {
  await getDashboardContext();
  const api = getAuthApiClient();
  const { items } = await api.listCampaigns();

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
          className="rounded-full bg-electric-cyan px-5 py-2.5 text-sm font-semibold text-electric-bg"
        >
          New campaign
        </Link>
      </header>

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
        className="mt-4 inline-block rounded-full bg-electric-cyan px-5 py-2 text-sm font-semibold text-electric-bg"
      >
        Create your first campaign
      </Link>
    </div>
  );
}

function CampaignCard({ campaign }: { campaign: Campaign }) {
  // "Expired" is computed locally — backend never auto-transitions, so a
  // campaign with ends_at in the past may still show status='active'. We
  // surface that distinction so the owner isn't surprised.
  const expired = isExpired(campaign);
  const tone = computeTone(campaign.status, expired);

  return (
    <Link
      href={`/dashboard/campaigns/${campaign.id}`}
      className="block rounded-2xl border border-electric-border bg-electric-surface p-4 shadow-sm transition hover:border-electric-cyan"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="font-display text-lg">{campaign.name}</p>
        <StatusBadge tone={tone}>
          {expired && campaign.status === "active" ? "Expired" : labelForStatus(campaign.status)}
        </StatusBadge>
      </div>
      <p className="mt-1 text-sm text-electric-text-muted">
        <strong>{campaign.multiplier}× stamps</strong> · {formatRange(campaign)}
      </p>
    </Link>
  );
}

function StatusBadge({
  tone,
  children,
}: {
  tone: "green" | "amber" | "grey" | "red";
  children: React.ReactNode;
}) {
  const styles =
    tone === "green"
      ? "bg-electric-cyan/10 text-electric-cyan"
      : tone === "amber"
        ? "bg-electric-cyan/15 text-electric-cyan"
        : tone === "red"
          ? "bg-red-500/10 text-red-300"
          : "bg-electric-surface-2 text-electric-text-muted";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${styles}`}>
      {children}
    </span>
  );
}

function computeTone(status: Campaign["status"], expired: boolean): "green" | "amber" | "grey" | "red" {
  if (expired && status === "active") return "grey";
  switch (status) {
    case "active":
      return "green";
    case "paused":
      return "amber";
    case "draft":
      return "grey";
    case "ended":
      return "red";
  }
}

function labelForStatus(status: Campaign["status"]): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function isExpired(c: Campaign): boolean {
  if (!c.ends_at) return false;
  const ts = Date.parse(c.ends_at);
  if (Number.isNaN(ts)) return false;
  return ts < Date.now();
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
